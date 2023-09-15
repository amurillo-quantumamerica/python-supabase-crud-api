from typing import Union
import bcrypt
from fastapi import FastAPI, UploadFile
from app.models import User
from db.supabase import create_supabase_client
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
from fastapi.responses import StreamingResponse
from io import BytesIO
import json

app = FastAPI()

origins = ['http://localhost:5173','https://supabase-fastapi-react.vercel.app/']

app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=['*'], allow_headers=['*'])

# Initialize supabase client
supabase = create_supabase_client()

def user_exists(key: str = "email", value: str = None):
    user = supabase.from_("users").select("*").eq(key, value).execute()
    return len(user.data) > 0

# Create a new user
@app.post("/user")
def create_user(user: User):
    try:
        # Convert email to lowercase
        user_email = user.email.lower()
        # Hash password
        hased_password = user.password

        # Check if user already exists
        if user_exists(value=user_email):
            return {"message": "User already exists"}

        # Add user to users table
        user = supabase.from_("users")\
            .insert({"name": user.name, "email": user_email, "password": hased_password})\
            .execute()
        
        # Check if user was added
        if user:
            return {"message": "User created successfully"}
        else:
            return {"message": "User creation failed"}
    except Exception as e:
        print("Error: ", e)
        return {"message": "User creation failed"}

@app.post("/upload_users")
def import_users(data : list[User]):
    results = []
    try:
        user = supabase.from_("users")\
        .insert([data])\
        .execute()
        if user:
            results.append({"message": f"Users created successfully"})
        else:
            results.append({"message": f"Users creation failed"})
    except Exception as e:
        print("Error: ", e)
        return {"message": "User creation failed"}
    if data:
        return {"message": f"{results}"}   
    

#Upload file, el parametro "file" que le pasamos debe coincidir con el de front 
@app.post('/upload_file')
async def  upload_file(file:UploadFile | None=None):
    message = ''
    if not file:
        message = "No upload file sent"
    else:
        if file.filename.endswith('.xlsx'):
            data = await file.read()
            excel_bytesio = BytesIO(data)
            df = pd.read_excel(excel_bytesio)
            json_data = df.to_json(orient='records')
            json_python = json.loads(json_data)
            try:
                user = supabase.from_("users")\
                .insert(json_python)\
                .execute()
                if user:
                    message = f"Users created successfully"
                else:
                    message= f"Users creation failed"
            except Exception as e:
                print("Error: ", e)
                message = "User creation failed"
                return {"message": f'{message}'}
    return {"message": f'{message}'}
    

#Retrieve JSON
@app.get("/xlsx_file")
def get_json_data():
    try:
        users = supabase.from_("users")\
            .select("id", "email", "name")\
            .execute()
        if users:
            data = users.data
            # Extract values from the list of dictionaries
            extracted_data = [(item["id"], item["email"], item["name"]) for item in data]
            df = pd.DataFrame(extracted_data, columns=["id", "email", "name"])
            buffer = BytesIO()
            with pd.ExcelWriter(buffer) as writer:
                df.to_excel(writer, index=False)
            return StreamingResponse(
            BytesIO(buffer.getvalue()),
            media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            headers={"Content-Disposition": f"attachment; filename=data.xlsx"}
            )

    except Exception as e:
        print(f"Error: {e}")
        return {"message": "User not found"}



#Retrieve CSV
@app.get("/csv")
def get_csv_data():
    df = pd.DataFrame(
        [["Canada", 10], ["USA", 20]], 
        columns=["team", "points"]
    )
    return StreamingResponse(
        iter([df.to_csv(index=False)]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=data.csv"}
)

# #Retrieve XLSX
@app.get("/xlsx")
def get_excel_data():
    df = pd.DataFrame(
        [["Canada", 10], ["USA", 20]], 
        columns=["team", "points"]
    )
    buffer = BytesIO()
    with pd.ExcelWriter(buffer) as writer:
        df.to_excel(writer, index=False)
    return StreamingResponse(
        BytesIO(buffer.getvalue()),
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={"Content-Disposition": f"attachment; filename=data.xlsx"}
)

# Retrieve a user
@app.get("/user")
def get_user(user_id: Union[str, None] = None):
    try:
        if user_id:
            user = supabase.from_("users")\
                .select("id", "name", "email")\
                .eq("id", user_id)\
                .execute()
            
            if user:
                return user
        else:
            users = supabase.from_("users")\
                .select("id", "email", "name")\
                .execute()
            if users:
                return users
    except Exception as e:
        print(f"Error: {e}")
        return {"message": "User not found"}


# Update a user
@app.put("/user")
def update_user(user_id: str, email: str, name: str):
    try:
        user_email = email.lower()

        # Check if user exists
        if user_exists("id", user_id):
            # Check if email already exists
            email_exists = supabase.from_("users")\
                .select("*").eq("email", user_email)\
                .execute()
            if len(email_exists.data) > 0:
                return {"message": "Email already exists"}

            # Update user
            user = supabase.from_("users")\
                .update({"name": name, "email": user_email})\
                .eq("id", user_id).execute()
            if user:
                return {"message": "User updated successfully"}
        else:
            return {"message": "User update failed"}
    except Exception as e:
        print(f"Error: {e}")
        return {"message": "User update failed"}

# Delete a user
@app.delete("/user")
def delete_user(user_id: str):
    try:        
        # Check if user exists
        if user_exists("id", user_id):
            # Delete user
            supabase.from_("users")\
                .delete().eq("id", user_id)\
                .execute()
            return {"message": "User deleted successfully"}
        
        else:
            return {"message": "User deletion failed"}
    except Exception as e:
        print(f"Error: {e}")
        return {"message": "User deletion failed"}