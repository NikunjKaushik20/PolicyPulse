import os
import sys
from pyngrok import ngrok
from dotenv import load_dotenv

# Load environment to check if key is present (optional)
load_dotenv()

def run_tunnel():
    # Set auth token from user input
    ngrok.set_auth_token("39I1YnrGtfFhTjc67MrLZqrP6uS_2DrfAVcf9GMjPWBfEKYCp")

    print("Starting ngrok tunnel for Twilio SMS...")
    
    # Open a HTTP tunnel on the default port 8000
    # http_tunnel = ngrok.connect(8000)
    # Twilio needs the URL
    try:
        public_url = ngrok.connect(8000).public_url
        print(f"\n✅ Tunnel Established: {public_url}")
        print("\n=== TWILIO CONFIGURATION INSTRUCTIONS ===")
        print(f"1. Go to Twilio Console > Phone Numbers > Active Numbers")
        print(f"2. Click on your phone number")
        print(f"3. Scroll to 'Messaging'")
        print(f"4. Under 'A MESSAGE COMES IN', set Webhook to:")
        print(f"   {public_url}/sms")
        print(f"5. Save configuration.")
        print("\nTunnel is active. Press Ctrl+C to stop.")
        
        # Keep process alive
        ngrok_process = ngrok.get_ngrok_process()
        ngrok_process.proc.wait()
    except Exception as e:
        print(f"❌ Error starting tunnel: {e}")
        print("Tip: You may need to sign up for a free ngrok account and run: `ngrok config add-authtoken <token>` if you hit rate limits.")

if __name__ == "__main__":
    run_tunnel()
