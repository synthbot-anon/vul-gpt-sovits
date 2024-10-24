import os

AUDIO_EXTENSIONS = {
    ".mp3", ".wav", ".flac", ".ogg"
}

def get_available_filename(filename):
    """
    Finds the first available filename by appending an incrementing digit.

    Args:
        filename: The desired filename without any extension.

    Returns:
        The first available filename with an appended digit if necessary.
    """

    extension = os.path.splitext(filename)[1]
    filename_base = filename.rsplit('.', 1)[0]

    i = 1
    while os.path.exists(f"{filename_base}{i}{extension}"):
        i += 1

    return f"{filename_base}{i}{extension}"


def sanitize_filename(input_string: str, max_length: int = 200) -> str:
    # Define a set of invalid characters
    invalid_chars = r'\/:*?"<>|'
    reserved_names = {
        "CON", "PRN", "AUX", "NUL", "COM1", "COM2", "COM3", "COM4",
        "COM5", "COM6", "COM7", "COM8", "COM9", "LPT1", "LPT2", "LPT3",
        "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"
    }
    
    # Replace invalid characters with an underscore
    sanitized = re.sub(f"[{re.escape(invalid_chars)}]", "_", input_string)
    
    # Trim leading and trailing spaces or dots
    sanitized = sanitized.strip().strip(".")
    
    # Check if the sanitized name is a reserved name and alter it if necessary
    if sanitized.upper() in reserved_names:
        sanitized = f"{sanitized}_file"
    
    # Ensure the length of the filename does not exceed the specified max length
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length].strip().strip(".")
    
    # If the resulting filename is empty, use a default name
    return sanitized or "default_filename"


def base64_to_audio_file(base64_string: str, output_file: str, codec: str = 'libvorbis'):
    # Step 1: Decode the base64 string to bytes
    audio_data = base64.b64decode(base64_string)

    # Step 2: Prepare an input stream using the decoded audio data
    input_buffer = BytesIO(audio_data)

    # Step 3: Open the input buffer with PyAV
    input_container = av.open(input_buffer, format='wav')  # Assume the base64 audio is in WAV format

    # Step 4: Create an output container to encode the audio
    output_container = av.open(output_file, mode='w')

    # Add an audio stream to the output container (e.g., OGG with libvorbis codec)
    output_stream = output_container.add_stream(codec, rate=44100)
    output_stream.bit_rate = 256000 # functionally lossless

    for frame in input_container.decode(audio=0):
        # Step 5: Resample the frame if necessary (match input and output formats)
        frame.sample_rate = 44100
        frame.format = 'fltp'

        # Step 6: Encode the frame and write to the output file
        for packet in output_stream.encode(frame):
            output_container.mux(packet)

    # Flush and close the output stream
    output_container.close()
    
    
def ppp_parse(fname):
    ret = {}
    split = os.path.basename(fname).split('_')
    try:
        ret['hour'] = split[0]
        ret['min'] = split[1]
        ret['sec'] = split[2]
        ret['char'] = split[3]
        ret['emotion'] = split[4]
        ret['noise'] = split[5]
        ret['transcr'] = os.path.splitext(''.join(split[6:]))[0]
    except IndexError as e:
        return None
    return ret