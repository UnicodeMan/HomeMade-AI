* **I. Create directories and clone repository**

a) Create a directory "AI_chatbot" (may be named differently or be in a different location)

`mkdir -p ~/AI`

b) Create a directory that will house persistant storage for AI to access, that will have python venv, that AI will mainly work in, that will not be deleted when docker containers are removed

`mkdir -p ~/AI/data`

c) Create a directory for postgresql database data:

`mkdir -p ~/AI/postgresql-data`

d) (Optional) You may create additional directories that you will plug to the container and specify in Volumes: section 

e) Clone the repository:

`cd ~/AI`

`git clone https://github.com/UnicodeMan/HomeMade-AI.git`

* **II. Modify docker-compose.yml**

a) In these lines, replace "NONE" with your API keys, and "POSTGRES_PASSWORD", with a password you want to create 
```environment:
      OPENAI_API_KEY: NONE
      GENAI_API_KEY: NONE
      HF_API_KEY: NONE
      DATABASE_URL: postgres://postgres:POSTGRES_PASSWORD@postgres:5432/ai_chatbot

/.../

  postgres:
    image: postgres:13-alpine
    container_name: ai-backend-postgres
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: POSTGRES_PASSWORD
      POSTGRES_DB: ai_chatbot
```
b) Change relevant volume directories in sections `volumes:` like this:
` - /full/path/to/directory:/do/not/change/this/part`

c) Review limits part: You may need to adjust limits of you backend, the RAM and CPU core values depending on your system.
* **III. Modify Dockerfile**

a) Modify first line to fetch required image architecture (armv8 will likely not be right for you)

b) Comment out lines that are specific to ROCKCHIP (your device is likely different)

c) (Optional) Review if added repositories and software reflect your needs

* **IV. Start the Backend!**

a) Change directory to ~/AI/HomeMade-AI

b) run docker-compose up

