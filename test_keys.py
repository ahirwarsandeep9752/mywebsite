from dotenv import load_dotenv
load_dotenv()
import os

print("RAZORPAY_KEY_ID =", os.getenv("RAZORPAY_KEY_ID"))
print("RAZORPAY_KEY_SECRET =", os.getenv("RAZORPAY_KEY_SECRET"))
