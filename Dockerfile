FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    fonts-dejavu-core \
    fonts-dejavu-extra \
    wget \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /usr/share/fonts/truetype/poppins && \
    wget -q "https://github.com/google/fonts/raw/main/ofl/poppins/Poppins-Regular.ttf" -O /usr/share/fonts/truetype/poppins/Poppins-Regular.ttf && \
    wget -q "https://github.com/google/fonts/raw/main/ofl/poppins/Poppins-Bold.ttf" -O /usr/share/fonts/truetype/poppins/Poppins-Bold.ttf && \
    wget -q "https://github.com/google/fonts/raw/main/ofl/poppins/Poppins-SemiBold.ttf" -O /usr/share/fonts/truetype/poppins/Poppins-SemiBold.ttf && \
    wget -q "https://github.com/google/fonts/raw/main/ofl/poppins/Poppins-ExtraBold.ttf" -O /usr/share/fonts/truetype/poppins/Poppins-ExtraBold.ttf && \
    wget -q --content-disposition "https://github.com/googlefonts/noto-emoji/releases/download/v2.042/Noto-Emoji.zip" -O /tmp/noto.zip || true

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .
COPY template.jpg .

EXPOSE 5000

CMD ["python", "app.py"]
