# consts
SERVER_DB_FILE = "gptsovits_data.db"
CLIENT_DB_FILE = "gptsovits_client_data.db"

from peewee import *
from typing import Optional

db = SqliteDatabase(None)

class BaseModel(Model):
    class Meta:
        database = db
        
class RefAudio(BaseModel):
    audio_hash = CharField(max_length=64, primary_key=True)
    local_filepath = TextField()
    utterance = TextField(null=True)
    character = TextField(null=True)
    list_position = IntegerField(null=True)

class GPTSovitsDatabase:
    def __init__(self, db_file):
        db.init(db_file)
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
        return [a for a in RefAudio.select()]
        
    def update_with_ref_audio(self,
        audio_hash: str,
        local_filepath: str,
        utterance: Optional[str] = None,
        character: Optional[str] = None,
        list_position: Optional[int] = None):
        ref_audio = self.get_ref_audio(audio_hash)
        if ref_audio is not None:
            ref_audio.local_filepath = local_filepath
            ref_audio.utterance = utterance
            ref_audio.character = character
            ref_audio.list_position = list_position
            ref_audio.save()
        else:
            ref_audio = RefAudio.create(
                audio_hash=audio_hash,
                local_filepath=local_filepath,
                utterance=utterance,
                character=character,
                list_position=list_position)
            
    def test_hashes(hashes: list[str]):
        r: RefAudio
        known_hashes = {r.audio_hash for r in self.list_ref_audio()}
        return {h: (h in known_hashes) for h in hashes}