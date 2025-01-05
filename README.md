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
This is a dockerized AI backend project that uses Google's genai API and huggingface inference API, using a modular approach that will allow me to plug more APIs in the future. Provider and model is selectable via pages' interface. The backend allows execution of scripts or code by parsing models' response and checking for [EXECUTE][/EXECUTE] and [PYTHON][/PYTHON] tags. You can also monitor the AIs commands and command output it receives. It has full access to the internet. The AI model has a local python environment, it can install any library it needs via pip3 comnmand.

**Todo:**
* **Many things are hard-coded...** ...in code, and that is sub-optimal for scalable and customizable use. I should use config class with config file, that has revelant configuration options. Internal API rate-limit is somewhat hard-coded. I will need to create json files for popular models and implement adaptable json limit parameter change based on APIs behaviour.
* **Some features may not fail gracefully.**
* **App's console output is used for debugging, and the content it outputs is a mess.** I need to figure out a robust way to log different aspects of the backend, also include configurable verbosity. For now, as this is a work-in-progress, logging will change depending on what is revelant for developer to see.
* **Frontend is unfinished.** It lacks many features, simultaneous multi-user and multi-session support, multimedia support, non-buggy message saving that would work accross sessions. The user interfaces design itself is buggy and unfinished.
* **Code execution:** I have no good knowledge to know how well the ai's environment is isolated, and if it could escape it. This needs more granular, configurable control for the sake of security. I should isolate the AI's environent by creating seperate docker inside backends docker that it would use, so API port and backends source code is inacessible.
* **Security implications and possible damage** This is very unsafe, not well tested, but a work in progress and a demonstration of possibilities. Run it with great caution.  