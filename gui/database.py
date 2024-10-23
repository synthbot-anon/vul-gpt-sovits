# consts
DB_FILE = "gptsovits_data.db"

from peewee import *
from typing import Optional

db = SqliteDatabase(DB_FILE)

class BaseModel(Model):
    class Meta:
        database = db
        
class RefAudio(BaseModel):
    audio_hash = CharField(max_length=64, primary_key=True)
    local_filepath = TextField()
    utterance = TextField(null=True)

class GPTSovitsDatabase:
    def __init__(self):
        db.connect()
        db.create_tables([RefAudio])
        
    def get_ref_audio(self, 
        audio_hash: str):
        try:
            return RefAudio.get(RefAudio.audio_hash == audio_hash)
        except RefAudio.DoesNotExist:
            return None
    
    def list_ref_audio(
        self):
        return RefAudio.select()
        
    def update_with_ref_audio(self,
        audio_hash: str,
        local_filepath: str,
        utterance: Optional[str]):
        ref_audio = RefAudio.create(
            audio_hash=audio_hash,
            local_filepath=local_filepath,
            utterance=utterance)