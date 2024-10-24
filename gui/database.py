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
    emotion = TextField(null=True)
    list_position = IntegerField(null=True)
    duration = FloatField(null=True)
    is_deleted = BooleanField(default=False)

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
        emotion: Optional[str] = None,
        list_position: Optional[int] = None,
        duration: Optional[float] = None,
        override_delete: Optional[bool] = None):
        ref_audio = self.get_ref_audio(audio_hash)
        if ref_audio is not None:
            # Avoid overwriting these items
            if ref_audio.local_filepath is None:
                ref_audio.local_filepath = local_filepath
            if ref_audio.utterance is None:
                ref_audio.utterance = utterance
            if ref_audio.character is None:
                ref_audio.character = character
            if ref_audio.emotion is None:
                ref_audio.emotion = emotion
            if ref_audio.list_position is None:
                ref_audio.list_position = list_position
            if ref_audio.duration is None:
                ref_audio.duration = duration
            if override_delete is not None:
                ref_audio.is_deleted = override_delete
            ref_audio.save()
        else:
            ref_audio = RefAudio.create(
                audio_hash=audio_hash,
                local_filepath=local_filepath,
                utterance=utterance,
                character=character,
                emotion=emotion,
                duration=duration,
                list_position=list_position)
        return ref_audio
            
    def test_hashes(hashes: list[str]):
        r: RefAudio
        known_hashes = {r.audio_hash for r in self.list_ref_audio()}
        return {h: (h in known_hashes) for h in hashes}