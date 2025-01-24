**Introduction:**

Ever wished you could mix-and-match AI models from different providers? This project delivers a FastAPI backend that acts as a single point of access for multiple AI APIs. Through an intuitive chat interface, users can experiment with different models, keep track of chat conversations and commands executed by the AI on the system. This project allows users to review both chat and system interactions and offers a unique way of interacting with AI.

**Contributions**

Contributions and expertise are more than welcome. I hope that this project will gain traction and be a collaborative effort in the future.

**About project:**

This is a dockerized AI backend project that can:
- Use Google's **genai API** and **huggingface inference API**, using a modular approach that will allow me to plug more APIs in the future. 
- Selectable provider and model via pages' interface. 
- Execution of scripts or code by parsing models' response and checking for `[EXECUTE][/EXECUTE]` and `[PYTHON][/PYTHON]` tags. 
- **Monitor** AI commands and command output it receives. 
- Install required python libraries on-the-fly: **full access to the internet** and **local python environment** enables the AI to install any library it needs via pip3 command.

**Usage**
If you want to take this for a test-spin, refer to `BUILDING.md`.

**Todo:**
* **Some things are hard-coded** in code, and that is sub-optimal for scalable and customizable use. 
* **Some features may not fail gracefully.**
* **App's console output is used for debugging, and the content it outputs is a mess.** This is not revelant if you're using webpage interface. In there, it provides clean information.
* **Frontend/backend is not polished.** It lacks many features, simultaneous multi-user and multi-session support, multimedia support, non-buggy message saving that would work accross sessions. The user interfaces design itself is somewhat unfinished, but quite functional
* **Code execution:** I have no good knowledge to know how well the ai's environment is isolated, and if it could escape it. This needs more granular, configurable control for the sake of security. I should isolate the AI's environent by creating seperate docker inside backends docker that it would use, so API port and backends source code is inacessible.
* **Security implications and possible damage** This is unsafe, not ready for production use, but a work in progress and a demonstration of possibilities. Run it with great caution, and do not make the website you host accessible on the internet.  