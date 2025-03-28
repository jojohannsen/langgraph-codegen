# app/auth.py

import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from jose import JWTError, jwt
from pydantic import EmailStr

from . import crud, models, schemas
from .database import get_db
from .config import settings
# Import components and layout helpers
from .components.molecules.forms import LoginForm, RegistrationForm
from .main import ft_html_response, AuthAwarePageWrapper # Import response helper and wrapper

# --- Configuration ---
ACCESS_TOKEN_COOKIE_NAME = "access_token"

# --- Password Hashing ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against a hashed password."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hashes a plain password."""
    return pwd_context.hash(password)

# --- JWT Token Handling ---
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Creates a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        # Default expiration time from settings
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt

def verify_token(token: str, credentials_exception: HTTPException) -> schemas.TokenData:
    """Decodes and verifies a JWT token."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        username: str | None = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = schemas.TokenData(username=username)
    except JWTError:
        raise credentials_exception
    return token_data

# --- Authentication Dependencies ---
async def get_token_from_cookie(request: Request) -> Optional[str]:
    """Dependency to extract token from HttpOnly cookie."""
    return request.cookies.get(ACCESS_TOKEN_COOKIE_NAME)

async def get_current_user(
    token: Optional[str] = Depends(get_token_from_cookie),
    db: Session = Depends(get_db)
) -> Optional[models.User]:
    """
    Dependency to get the current user from the token in the cookie.
    Returns the User object or None if not authenticated or token is invalid.
    """
    if token is None:
        return None

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"}, # Standard header, though we use cookies
    )
    try:
        token_data = verify_token(token, credentials_exception)
    except HTTPException:
        # If token verification fails, treat as unauthenticated
        return None

    user = crud.get_user_by_username(db, username=token_data.username)
    if user is None:
        # User might have been deleted after token was issued
        return None
    return user

async def get_current_active_user(
    current_user: Optional[models.User] = Depends(get_current_user)
) -> Optional[models.User]:
    """
    Dependency to get the current active user. If the user is inactive,
    it's treated as None (unauthenticated for practical purposes in UI).
    If authentication is required and fails/user inactive, raise 401 in the endpoint itself.
    """
    if current_user and not current_user.is_active:
        # Consider inactive user as not logged in for most UI purposes
        return None
    return current_user

# --- Router ---
router = APIRouter()

# --- Registration ---
@router.get("/register", response_class=HTMLResponse)
async def register_form(request: Request, current_user: models.User | None = Depends(get_current_active_user)):
    """Displays the registration form."""
    if current_user:
        # If already logged in, redirect to home
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    form = RegistrationForm(action="/register")
    page_content = AuthAwarePageWrapper(form, current_user=None) # Pass None explicitly
    return ft_html_response(request, page_content, title="Register")

@router.post("/register", response_class=HTMLResponse)
async def register_user(request: Request, db: Session = Depends(get_db)):
    """Handles user registration form submission."""
    form_data = await request.form()
    username = form_data.get("username")
    email = form_data.get("email")
    password = form_data.get("password")
    password_confirm = form_data.get("password_confirm")

    errors = {}
    submitted_data = {"username": username, "email": email} # Don't send back passwords

    # Basic Validations
    if not username: errors["username"] = "Username is required."
    if not email: errors["email"] = "Email is required."
    if not password: errors["password"] = "Password is required."
    if password != password_confirm: errors["password_confirm"] = "Passwords do not match."
    # Add more validation (e.g., password complexity) here if needed

    # Validate Email Format
    try:
        if email: EmailStr.validate(email)
    except ValueError:
        errors["email"] = "Invalid email format."

    # Check if user or email already exists
    if username and crud.get_user_by_username(db, username=username):
        errors["username"] = "Username already taken."
    if email and crud.get_user_by_email(db, email=email):
        errors["email"] = "Email already registered."

    if errors:
        # Re-render form with errors
        form = RegistrationForm(action="/register", errors=errors, data=submitted_data)
        page_content = AuthAwarePageWrapper(form, current_user=None)
        # Use status 400 for bad request
        response = ft_html_response(request, page_content, title="Register - Errors")
        response.status_code = status.HTTP_400_BAD_REQUEST
        return response

    # Create user if validation passes
    hashed_password = get_password_hash(password)
    user_in = schemas.UserCreate(username=username, email=email, password=hashed_password)
    try:
        crud.create_user(db=db, user=user_in)
    except Exception as e: # Catch potential DB errors
        # Log the error e
        print(f"Error creating user: {e}")
        errors["__general__"] = "An error occurred during registration. Please try again."
        form = RegistrationForm(action="/register", errors=errors, data=submitted_data)
        page_content = AuthAwarePageWrapper(form, current_user=None)
        response = ft_html_response(request, page_content, title="Register - Error")
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return response

    # Redirect to login page after successful registration
    # Optionally add a success message via query param or flash message system
    return RedirectResponse(url="/login?registered=true", status_code=status.HTTP_303_SEE_OTHER)


# --- Login ---
@router.get("/login", response_class=HTMLResponse)
async def login_form(
    request: Request,
    error: Optional[str] = None,
    registered: Optional[bool] = False,
    current_user: models.User | None = Depends(get_current_active_user)
):
    """Displays the login form."""
    if current_user:
        # If already logged in, redirect to home
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    success_message = "Registration successful! Please log in." if registered else None
    form = LoginForm(action="/login", error=error, success_message=success_message) # Pass messages to form component if it supports them
    page_content = AuthAwarePageWrapper(form, current_user=None)
    return ft_html_response(request, page_content, title="Login")


@router.post("/login") # No HTMLResponse here, we redirect or set cookie
async def login_user(
    response: Response, # Inject Response object to set cookies
    db: Session = Depends(get_db),
    username: str = Form(...), # Use Form for direct access
    password: str = Form(...)
):
    """Handles user login form submission and sets auth cookie."""
    user = crud.authenticate_user(db, username=username, password=password)

    if not user:
        # Redirect back to login form with an error message
        # Using query parameters for simplicity here
        error_message = "Incorrect username or password"
        # Ensure URL encoding for the error message if needed, but simple strings are usually fine
        return RedirectResponse(
            url=f"/login?error={error_message}",
            status_code=status.HTTP_303_SEE_OTHER
        )

    if not user.is_active:
         # Redirect back to login form with an inactive error message
        error_message = "Account is inactive"
        return RedirectResponse(
            url=f"/login?error={error_message}",
            status_code=status.HTTP_303_SEE_OTHER
        )

    # Create JWT token
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )

    # Set HttpOnly cookie in the response
    response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        key=ACCESS_TOKEN_COOKIE_NAME,
        value=access_token,
        httponly=True, # Crucial for security
        max_age=int(access_token_expires.total_seconds()), # Optional: Set cookie expiry
        expires=int(access_token_expires.total_seconds()), # For older browsers
        samesite="lax", # Good default for security vs usability balance
        # secure=True, # IMPORTANT: Uncomment this in production when using HTTPS
        path="/"
    )
    return response


# --- Logout ---
@router.post("/logout") # Use POST for logout to prevent CSRF via GET requests
async def logout_user():
    """Logs the user out by clearing the auth cookie."""
    response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(
        key=ACCESS_TOKEN_COOKIE_NAME,
        # Ensure path and domain match how the cookie was set if they were specified
        path="/"
        # domain="yourdomain.com" # Add if you set a domain when creating cookie
    )
    return response


# --- Helper for requiring authentication in routes ---
# You can use this dependency in specific routes that absolutely require login
async def get_required_current_active_user(
    current_user: Optional[models.User] = Depends(get_current_active_user)
) -> models.User:
    """
    Dependency that requires a user to be authenticated and active.
    Raises 401 Unauthorized if not logged in or inactive.
    """
    if current_user is None:
        # Option 1: Redirect to login
        # return RedirectResponse(url="/login?next=requested_path", status_code=status.HTTP_302_FOUND)
        # Option 2: Raise 401 (more API-like, can be handled by frontend/htmx)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return current_user