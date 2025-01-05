**WARNING:**

This software is experimental and potentially dangerous. It is provided "as-is" without any warranties or guarantees.

**Important:**

* **High Risk:** This software may produce unexpected and potentially harmful outputs that may harm your system. Use with extreme caution.

* **Careful Monitoring:** It is essential to closely monitor the software's behavior and outputs.

* **Isolation:** Run this software in a secure and isolated environment to minimize potential harm.

* **No Liability:** The author is not responsible for any damages arising from the use of this software.

By using this software, you acknowledge these risks and agree to use it responsibly.

**Disclaimer:**
This is work-in-progress, that has a lot of features missing, unfinished, or just too basic for reliable and comfortable use.
This project and its code is created with use of AI.

**About project:**
This is a dockerized AI backend project that uses Google's genai API. The backend allows execution of scripts or code by parsing models response and checking for [EXECUTE][/EXECUTE] and [PYTHON][/PYTHON] tags. You can also monitor the AIs commands and command output it receives. It has extensive access to the internet.

**Todo:**
* **Many things are hard-coded** in code, and that is sub-optimal for scalable and customizable use. I should use config class with config file, that has revelant configuration options. Internal API rate-limit is hardcoded, i should figure out if its possible to apply it dynamically by gathering revelant data using the API library.
* **Some features may not fail gracefully.**
* **App's console ouptup is used for debugging, and the content it outputs is a mess.** I need to figure out a robust way to log different aspects of the backend, also include configurable verbosity.
* **Frontend is unfinished.** It lacks many features, like ratelimiting indication, code execution indication, better handling of sessions, simultaneous multi-user and multi-session support, secure way to send messages via API (right now it sends via url option, like `url/...?message=possibly_private_information`). The user interface itself is buggy and unfinished.
* **Code execution:** I have no good knowledge to know how well the ai's environment is isolated, and if it could escape it. This needs more granular, configurable control for the sake of security. I should isolate the AI's environent by creating seperate docker inside backends docker that it would use, so API port is inacessible.
* **Security implications and possible damage** This is very unsafe, not well tested, but a work in progress and a demonstration of possibilities. Run it with great caution.  