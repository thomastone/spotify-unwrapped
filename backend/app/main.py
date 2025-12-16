from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlmodel import Session, select, insert
from contextlib import asynccontextmanager
from typing import Annotated, Optional, Any
import polars as pl
import json

from .data_processor import parse_files_to_df, generate_dashboard_stats
from .db.engine import create_db_and_tables, engine
from .db.models import User, StreamingHistory, DashboardCache, RequestCache
from .auth import get_password_hash, verify_password, create_access_token, SECRET_KEY, ALGORITHM
from jose import JWTError, jwt
from datetime import datetime

# Lifecycle event to create DB tables on startup
@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield

app = FastAPI(lifespan=lifespan)

# Crucial for allowing Next.js on port 3000 to talk to FastAPI on port 8000
origins = [
    "http://localhost:3000",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Schema overrides for Polars to handle sparse data from DB correctly
# This prevents inference errors when the first batch of rows contains Nulls
DB_SCHEMA_OVERRIDES = {
    "platform": pl.Utf8,
    "ms_played": pl.Int64,
    "conn_country": pl.Utf8,
    "ip_addr": pl.Utf8,
    "master_metadata_track_name": pl.Utf8,
    "master_metadata_album_artist_name": pl.Utf8,
    "master_metadata_album_album_name": pl.Utf8,
    "spotify_track_uri": pl.Utf8,
    "episode_name": pl.Utf8,
    "episode_show_name": pl.Utf8,
    "spotify_episode_uri": pl.Utf8,
    "reason_start": pl.Utf8,
    "reason_end": pl.Utf8,
    "shuffle": pl.Boolean,
    "skipped": pl.Boolean,
    "offline": pl.Boolean,
    "offline_timestamp": pl.Int64,
    "incognito_mode": pl.Boolean,
}

def get_session():
    with Session(engine) as session:
        yield session

def save_stats_to_cache(session: Session, user_id: int, stats: dict):
    cache = session.exec(select(DashboardCache).where(DashboardCache.user_id == user_id)).first()
    if cache:
        cache.data = stats
        cache.updated_at = datetime.utcnow()
        session.add(cache) # Ensure it's marked for update
    else:
        cache = DashboardCache(user_id=user_id, data=stats)
        session.add(cache)
    session.commit()

def get_request_cache(session: Session, user_id: int, key: str):
    return session.exec(select(RequestCache).where(RequestCache.user_id == user_id, RequestCache.key == key)).first()

def save_request_cache(session: Session, user_id: int, key: str, data: Any):
    cache = get_request_cache(session, user_id, key)
    if cache:
        cache.data = data
        cache.updated_at = datetime.utcnow()
        session.add(cache)
    else:
        cache = RequestCache(user_id=user_id, key=key, data=data)
        session.add(cache)
    session.commit()

async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], session: Session = Depends(get_session)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = session.exec(select(User).where(User.username == username)).first()
    if user is None:
        raise credentials_exception
    return user

@app.get("/")
def read_root():
    return {"status": "Backend running successfully!"}

@app.post("/token")
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: Session = Depends(get_session)
):
    user = session.exec(select(User).where(User.username == form_data.username)).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/register")
def register(user: User, session: Session = Depends(get_session)):
    # Check if user exists
    existing_user = session.exec(select(User).where(User.username == user.username)).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    user.hashed_password = get_password_hash(user.hashed_password)
    session.add(user)
    session.commit()
    session.refresh(user)
    return {"username": user.username, "email": user.email}

@app.post("/api/process")
async def process_files(
    files: list[UploadFile] = File(...), 
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")
    
    file_contents = []
    for file in files:
        content = await file.read()
        file_contents.append(content)
    
    try:
        # 1. Parse uploaded files to Polars DataFrame
        new_df = parse_files_to_df(file_contents)
        
        if not new_df.is_empty():
            # 2. Add user_id to the DataFrame
            new_df = new_df.with_columns(pl.lit(current_user.id).alias("user_id"))
            
            # Filter columns to only those present in StreamingHistory model
            valid_columns = {
                "ts", "platform", "ms_played", "conn_country", "ip_addr", 
                "master_metadata_track_name", "master_metadata_album_artist_name", 
                "master_metadata_album_album_name", "spotify_track_uri", 
                "episode_name", "episode_show_name", "spotify_episode_uri", 
                "reason_start", "reason_end", "shuffle", "skipped", "offline", 
                "offline_timestamp", "incognito_mode", "user_id"
            }
            
            # Select only columns that exist in both the dataframe and the model
            cols_to_select = [col for col in new_df.columns if col in valid_columns]
            new_df = new_df.select(cols_to_select)
            
            # 3. Convert to list of dicts for insertion
            records = new_df.to_dicts()
            
            # 4. Bulk Insert
            session.execute(insert(StreamingHistory), records)
            session.commit()
        
        # 5. Retrieve ALL history for this user to generate updated stats
        # We fetch all rows for this user.
        # This might be heavy for very large histories, but is the most accurate way 
        # to show the dashboard reflecting "all time" stats.
        
        # Fetching as dicts/tuples is faster than objects for DataFrame creation
        statement = select(StreamingHistory).where(StreamingHistory.user_id == current_user.id)
        # We can use pandas read_sql or just iterate. 
        # Let's iterate over results.
        
        all_rows = session.exec(statement).all()
        
        if not all_rows:
            return generate_dashboard_stats(pl.DataFrame())

        # Convert SQLModel objects to dicts for Polars
        all_data = [row.model_dump() for row in all_rows]
        
        # Use from_dicts with schema_overrides to prevent inference errors on sparse data
        df_all = pl.from_dicts(all_data, schema_overrides=DB_SCHEMA_OVERRIDES)
        
        # 6. Generate Stats
        result = generate_dashboard_stats(df_all)
        
        # 7. Save to Cache
        save_stats_to_cache(session, current_user.id, result)
        
        # Clear Request Cache on new upload as data changed
        session.exec(text("DELETE FROM requestcache WHERE user_id = :uid"), params={"uid": current_user.id})
        session.commit()
        
        return result
        
    except Exception as e:
        print(f"Error processing files: {e}")
        # Rollback in case of error during insert
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stats")
async def get_stats(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    try:
        # 1. Check Cache
        cached_stats = session.exec(select(DashboardCache).where(DashboardCache.user_id == current_user.id)).first()
        if cached_stats:
            print(f"DEBUG: Returning cached stats for user {current_user.id}")
            return cached_stats.data
            
        print(f"DEBUG: Cache miss for user {current_user.id}, calculating...")

        # Fetch all rows for the user
        statement = select(StreamingHistory).where(StreamingHistory.user_id == current_user.id)
        all_rows = session.exec(statement).all()
        
        if not all_rows:
            return generate_dashboard_stats(pl.DataFrame())

        # Convert SQLModel objects to dicts for Polars
        all_data = [row.model_dump() for row in all_rows]
        
        # Use from_dicts with schema_overrides to prevent inference errors on sparse data
        df_all = pl.from_dicts(all_data, schema_overrides=DB_SCHEMA_OVERRIDES)
        
        # Generate Stats
        result = generate_dashboard_stats(df_all)
        
        # Save to Cache
        save_stats_to_cache(session, current_user.id, result)
        
        return result
    except Exception as e:
        print(f"Error fetching stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/songs")
async def get_songs(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    try:
        # Construct Cache Key
        s_date_str = start_date.strftime("%Y-%m-%d") if start_date else "None"
        e_date_str = end_date.strftime("%Y-%m-%d") if end_date else "None"
        cache_key = f"songs:{s_date_str}:{e_date_str}"
        
        # Check Cache
        cached = get_request_cache(session, current_user.id, cache_key)
        if cached:
            return cached.data

        query = select(StreamingHistory).where(StreamingHistory.user_id == current_user.id)
        
        if start_date:
            query = query.where(StreamingHistory.ts >= start_date)
        if end_date:
            query = query.where(StreamingHistory.ts <= end_date)
            
        rows = session.exec(query).all()
        
        if not rows:
            return []
            
        data = [row.model_dump() for row in rows]
        df = pl.from_dicts(data, schema_overrides=DB_SCHEMA_OVERRIDES)
        
        # Aggregate
        songs_df = (
            df.filter(pl.col("master_metadata_track_name").is_not_null())
            .group_by(["master_metadata_track_name", "master_metadata_album_artist_name"])
            .agg([
                pl.sum("ms_played").alias("total_ms"),
                pl.len().alias("play_count")
            ])
            .with_columns(
                (pl.col("total_ms") / 60000).round(1).alias("total_minutes")
            )
            .sort("total_ms", descending=True)
            .select([
                pl.col("master_metadata_track_name").alias("track"),
                pl.col("master_metadata_album_artist_name").alias("artist"),
                pl.col("total_ms"),
                pl.col("total_minutes"),
                pl.col("play_count")
            ])
        )
        
        result = songs_df.to_dicts()
        
        # Save to Cache
        save_request_cache(session, current_user.id, cache_key, result)
        
        return result
        
    except Exception as e:
        print(f"Error fetching songs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/songs/detail")
async def get_song_detail(
    track_name: str,
    artist_name: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    try:
        query = select(StreamingHistory).where(
            StreamingHistory.user_id == current_user.id,
            StreamingHistory.master_metadata_track_name == track_name
        )
        
        if artist_name:
            query = query.where(StreamingHistory.master_metadata_album_artist_name == artist_name)
            
        rows = session.exec(query).all()
        
        if not rows:
            raise HTTPException(status_code=404, detail="Song not found")
            
        data = [row.model_dump() for row in rows]
        df = pl.from_dicts(data, schema_overrides=DB_SCHEMA_OVERRIDES)
        
        # Summary Stats
        total_ms = df["ms_played"].sum()
        play_count = len(df)
        first_played = df["ts"].min()
        last_played = df["ts"].max()
        
        # History Graph Data (Daily)
        history_df = (
            df.sort("ts")
            .with_columns(pl.col("ts").dt.date().cast(pl.Utf8).alias("date"))
            .group_by("date")
            .agg(pl.sum("ms_played").alias("daily_ms"))
            .with_columns(
                (pl.col("daily_ms") / 60000).round(1).alias("minutes")
            )
            .sort("date")
            .select([
                pl.col("date").alias("x"),
                pl.col("minutes").alias("y")
            ])
        )
        
        return {
            "stats": {
                "track": track_name,
                "artist": artist_name,
                "total_minutes": round(total_ms / 60000, 1),
                "play_count": play_count,
                "first_played": first_played,
                "last_played": last_played
            },
            "history": history_df.to_dicts()
        }
        
    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"Error fetching song detail: {e}")
        raise HTTPException(status_code=500, detail=str(e))
