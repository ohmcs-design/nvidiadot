# 🐳 DOT AI - Docker Setup & Sharing Guide (दोस्तों के साथ शेयर करने की गाइड)

यह गाइड बताती है कि आप **DOT AI** को Docker के ज़रिए अपने दोस्त को कैसे भेज सकते हैं और आपका दोस्त इसे सिर्फ 1 कमांड में कैसे चला सकता है।

---

## 📋 दोस्त के सिस्टम में क्या-क्या होना चाहिए? (Requirements)

आपके दोस्त के कंप्यूटर (Windows, Mac, या Linux) पर केवल यह होना चाहिए:
1. **[Docker Desktop](https://www.docker.com/products/docker-desktop/)** (Installed और Running).
2. **NVIDIA API Key** (Free key integrate.api.nvidia.com से या आपकी दी हुई key).
3. **Web Browser** (Google Chrome, Microsoft Edge, Brave, या Firefox).

> **Note:** दोस्त को Python, Node.js, C Compiler, या Java इंस्टॉल करने की **कोई ज़रूरत नहीं है** — Docker कंटेनर के अंदर सब कुछ पहले से ऑटोमैटिक सेटअप है!

---

## 📦 दोस्त को कैसे भेजें? (How to Send)

### Option 1: GitHub Link भेजें (सबसे आसान)
दोस्त को अपना GitHub रिपॉजिटरी लिंक भेजें:
```bash
git clone https://github.com/aryavartsubhammoharana/kyaredot.git
cd kyaredot
```

### Option 2: ZIP फाइल बनाकर भेजें
अगर दोस्त Git नहीं इस्तेमाल करता:
1. अपने प्रोजेक्ट फोल्डर की ZIP फाइल बनाएं (ध्यान रखें: `.env` फाइल को ZIP में न डालें ताकि आपकी पर्सनल API Key सुरक्षित रहे).
2. दोस्त को ZIP भेजें और वो उसे Extract कर ले.

---

## 🚀 Docker से कैसे चलाएं? (How to Run)

### विधि 1: Docker Compose (सिर्फ 1 कमांड में) — Recommended ⭐

1. फोल्डर में `workspace` नाम का एक फोल्डर बनाएं (या जिस प्रोजेक्ट पर काम करना है):
   ```bash
   mkdir workspace
   ```
2. सिर्फ यह कमांड चलाएं:
   ```bash
   docker-compose up --build
   ```
3. ब्राउज़र में खोलें:
   👉 **http://localhost:8080**

---

### विधि 2: Standard Docker Commands

1. **Docker Image Build करें:**
   ```bash
   docker build -t kyaredot .
   ```

2. **Container Run करें:**
   * **Windows PowerShell:**
     ```powershell
     docker run -d -p 8080:8080 -p 8765:8765 -e NVIDIA_API_KEY="nvapi-YOUR_KEY" -v ${PWD}/workspace:/workspace --name dot-ide kyaredot
     ```
   * **Linux / macOS:**
     ```bash
     docker run -d -p 8080:8080 -p 8765:8765 -e NVIDIA_API_KEY="nvapi-YOUR_KEY" -v "$(pwd)/workspace:/workspace" --name dot-ide kyaredot
     ```

3. ब्राउज़र में खोलें:
   👉 **http://localhost:8080**

---

## 🔑 NVIDIA API Key कैसे सेट करें?

दोस्त के पास 2 आसान विकल्प हैं:

1. **ब्राउज़र UI से (सबसे आसान):**
   - `http://localhost:8080` खोलें.
   - ऊपर दाईं तरफ हरे रंग के **"NVIDIA API"** बटन पर क्लिक करें.
   - अपनी `nvapi-...` key पेस्ट करके **Save Settings** पर क्लिक करें.

2. **`.env` फाइल बनाकर:**
   - प्रोजेक्ट फोल्डर में `.env` फाइल बनाएं:
     ```env
     NVIDIA_API_KEY=nvapi-your-key-here
     ```

---

## 📁 दोस्त अपने कंप्यूटर का कोई भी प्रोजेक्ट कैसे खोले?

अगर दोस्त अपने कंप्यूटर के किसी खास फोल्डर (जैसे `D:\MyWebsite` या `/home/user/myproject`) पर AI से काम कराना चाहता है, तो वो volume mount में अपना पाथ दे सकता है:

```bash
docker run -p 8080:8080 -v "D:/MyWebsite:/workspace" kyaredot
```
अब कंटेनर के अंदर उसका पूरा प्रोजेक्ट खुलेगा, AI फाइल्स को एडिट करेगा और चेंजेस सीधे उसके कंप्यूटर के फोल्डर में सेव होंगे!

---

## 🛑 कंटेनर बंद (Stop) करने के लिए:
```bash
docker-compose down
# या
docker stop dot-ide
```
