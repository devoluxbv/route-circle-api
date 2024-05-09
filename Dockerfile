FROM ubuntu:22.04

# Set non-interactive timezone configuration
ENV DEBIAN_FRONTEND=noninteractive

# Set the working directory in the container
WORKDIR /app

# Install Python, pip, and essential build tools
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    libpq-dev python3-dev \
    python3-setuptools \
    nano

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip3 install --no-cache-dir -r requirements.txt

EXPOSE 5000

CMD ["python3", "app.py"]
