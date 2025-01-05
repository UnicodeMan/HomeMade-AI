# Use an ARM64 base image

# REPLACE armv8 WITH ARCHITECTURE OF YOUR CHOICE
FROM arm64v8/ubuntu:24.04

# Set the working directory in the container
WORKDIR /app

# Set environment variables to avoid interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# Install required system dependencies
RUN apt-get update && \
    apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    gstreamer1.0-tools \
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good \
    ffmpeg \
    libgstreamer1.0-dev \
    libgstreamer-plugins-base1.0-dev \
    libavcodec-dev \
    libavformat-dev \
    libavdevice-dev \
    libswscale-dev \
    libv4l-dev \
    libdrm-dev \
    libudev-dev \
    libvulkan-dev \
    libgles2-mesa-dev \
    libpython3-dev \
    mesa-utils \
    && apt-get clean


# Install Python libraries using apt
RUN apt-get update && \
    apt-get install -y \
    python3-numpy \
    python3-opencv \
    python3-scipy \
#    python3-tensorflow \
    python3-pandas \
    python3-flask \
    python3-flask-cors \
    python3-sklearn \
    python3-pillow \
    python3-requests \
    && apt-get clean
RUN apt install software-properties-common -y

# ROCKCHIP-SPECIFIC START:
RUN add-apt-repository ppa:liujianfeng1994/rockchip-multimedia -y
RUN apt update
RUN apt install libv4l-0 -y
RUN apt install librockchip-mpp-dev -y
RUN apt install librga-dev  -y
# ROCKCHIP-SPECIFIC END
RUN apt dist-upgrade -y
RUN apt install python3-fastapi python3-openai -y
RUN apt install python3-uvicorn uvicorn python3-redis -y
RUN pip3 install --break-system-packages google-generativeai slowapi
# Create a non-sudo user 'ai'
RUN useradd -ms /bin/bash ai
# Enable multiverse, universe, and restricted repositories
RUN sed -i 's/# deb.*multiverse/deb.*multiverse/g' /etc/apt/sources.list && \
    sed -i 's/# deb.*universe/deb.*universe/g' /etc/apt/sources.list && \
    sed -i 's/# deb.*restricted/deb.*restricted/g' /etc/apt/sources.list

RUN apt-get update && \
    apt-get install -y \
        apt \
        bash \
        openssh-server \
        vim \
        nano \
        tmux \
        screen \
        net-tools \
        curl \
        wget \
        tar \
        xz-utils \
        grep \
        sed \
        gawk \
        systemd \
        rsync \
        strace \
        ltrace \
        htop \
        iotop \
        nmap \
        tcpdump \
        wireshark \
        iptables \
        nftables \
        fail2ban \
        logrotate \
        jq \
        tree \
        ncdu \
        pv \
        most \
        tldr \
        shellcheck \
        tmuxinator \
        zsh \
        fzf \
        ripgrep \
        bat \
        coreutils \
        eza
RUN apt install proot -y
WORKDIR /data
RUN mkdir -p /home/ai
RUN chown ai:ai /home/ai
RUN chown ai:ai /data
USER ai
WORKDIR /data
# set up python venv if it doesnt exist
RUN [ ! -f "/data/venv" ] && python3 -m venv /mnt/persistent_storage/venv

# Set the working directory where backend is located
WORKDIR /app/
EXPOSE 8000

USER root
RUN chown root:root /app -R
RUN chmod 700 /app -R
# for arm64 chromium and chromium-driver
RUN add-apt-repository ppa:xtradeb/apps -y
RUN apt install chromium chromium-driver -y
RUN apt install lsof -y
RUN apt install python3-aioredis -y
# Command to run your backend.py script
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
