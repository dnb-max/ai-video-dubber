import os
import requests
import subprocess
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from openai import OpenAI

app = FastAPI()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

VOICE_IDS = {
    "Hindi": "21m00Tcm4TlvDq8ikWAM",
    "English": "EXAVITQu4vr4xnSDxMaL",
    "Japanese": "AZnzlk1XvdvUeBnXmlld",
    "Korean": "21m00Tcm4TlvDq8ikWAM",
    "Chinese": "21m00Tcm4TlvDq8ikWAM",
    "Nepali": "21m00Tcm4TlvDq8ikWAM"
}

@app.get("/", response_class=HTMLResponse)
async def home():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>AI Video Dubbing Studio</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { font-family: Arial; background: #0f172a; color: white; display:flex; justify-content:center; align-items:center; min-height:100vh; margin:0; padding: 20px; }
            .box { background: #1e293b; padding: 25px; border-radius: 12px; width: 100%; max-width: 400px; text-align: center; }
            select, input, button { width: 100%; margin-top: 15px; padding: 12px; border-radius: 8px; border: none; box-sizing: border-box; }
            button { background: #2563eb; color: white; font-weight: bold; cursor: pointer; }
            #status { margin-top: 15px; color: #60a5fa; }
        </style>
    </head>
    <body>
        <div class="box">
            <h2>AI Video Dubbing Studio</h2>
            <form id="dubForm">
                <input type="file" id="videoFile" accept="video/*" required>
                <select id="language">
                    <option value="Hindi">Hindi</option>
                    <option value="English">English</option>
                    <option value="Japanese">Japanese</option>
                    <option value="Korean">Korean</option>
                    <option value="Chinese">Chinese</option>
                    <option value="Nepali">Nepali</option>
                </select>
                <button type="submit">Start AI Dubbing</button>
            </form>
            <div id="status"></div>
        </div>
        <script>
            document.getElementById('dubForm').addEventListener('submit', async (e) => {
                e.preventDefault();
                const status = document.getElementById('status');
                status.innerText = "Processing video... Please wait a few minutes.";
                
                const formData = new FormData();
                formData.append('file', document.getElementById('videoFile').files[0]);
                formData.append('target_language', document.getElementById('language').value);

                try {
                    const response = await fetch('/dub-video/', { method: 'POST', body: formData });
                    if(response.ok) {
                        const blob = await response.blob();
                        const url = window.URL.createObjectURL(blob);
                        status.innerHTML = `<a href="${url}" download="dubbed_video.mp4" style="color: #4ade80; font-weight: bold;">Download Dubbed Video</a>`;
                    } else {
                        status.innerText = "Error processing video. Check API keys.";
                    }
                } catch(err) {
                    status.innerText = "Server Error: " + err.message;
                }
            });
        </script>
    </body>
    </html>
    """

@app.post("/dub-video/")
async def dub_video(file: UploadFile = File(...), target_language: str = Form(...)):
    try:
        input_video = f"temp_{file.filename}"
        extracted_audio = "temp_audio.mp3"
        dubbed_audio = "temp_dubbed.mp3"
        output_video = "final_output.mp4"

        with open(input_video, "wb") as f:
            f.write(await file.read())

        subprocess.run(f"ffmpeg -y -i \"{input_video}\" -q:a 0 -map a \"{extracted_audio}\"", shell=True, check=True)

        client = OpenAI(api_key=OPENAI_API_KEY)
        with open(extracted_audio, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(model="whisper-1", file=audio_file)

        prompt = f"Translate the following text to {target_language} naturally for voice dubbing:\n\n{transcript.text}"
        translation = client.chat.completions.create(model="gpt-4o", messages=[{"role": "user", "content": prompt}])
        translated_text = translation.choices[0].message.content

        voice_id = VOICE_IDS.get(target_language, "21m00Tcm4TlvDq8ikWAM")
        tts_url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        tts_res = requests.post(
            tts_url,
            json={"text": translated_text, "model_id": "eleven_multilingual_v2"},
            headers={"Accept": "audio/mpeg", "Content-Type": "application/json", "xi-api-key": ELEVENLABS_API_KEY}
        )
        with open(dubbed_audio, "wb") as f:
            f.write(tts_res.content)

        subprocess.run(f"ffmpeg -y -i \"{input_video}\" -i \"{dubbed_audio}\" -c:v copy -c:a aac -map 0:v:0 -map 1:a:0 \"{output_video}\"", shell=True, check=True)

        return FileResponse(output_video, media_type="video/mp4", filename="dubbed_video.mp4")

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
