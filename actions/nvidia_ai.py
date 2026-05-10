from core.llm_provider import generate_text

def nvidia_chat(parameters, player=None, speak=None):
    """
    Calls NVIDIA's API using the centralized llm_provider.
    """
    prompt = parameters.get("prompt", "")
    model = parameters.get("model", "z-ai/glm4.7")
    
    if not prompt:
        return "Sir, I need a prompt to communicate with the NVIDIA model."

    if player:
        player.write_log(f"[NVIDIA] Requesting analysis using {model}...")

    if speak:
        speak("Sir, I am requesting the analytical model's expertise.")

    try:
        response = generate_text(prompt, force_nvidia=True, nvidia_model=model)
        
        if player:
            player.write_log(f"[NVIDIA] Analysis complete ({len(response)} chars).")
            
        return response

    except Exception as e:
        err_msg = f"NVIDIA Analysis Error: {str(e)}"
        if player:
            player.write_log(f"ERR: {err_msg}")
        return err_msg

if __name__ == "__main__":
    # Test the module
    print("--- NVIDIA AI MODULE TEST ---")
    test_params = {"prompt": "Hello! Who are you and what model are you?"}
    result = nvidia_chat(test_params)
    print(f"Final Result:\n{result}")
