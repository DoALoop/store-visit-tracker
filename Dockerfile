
# Use the official Python image (non-slim variant to ensure build tools are available)
FROM python:3.10

# Allow statements and log messages to immediately appear in the Knative logs
ENV PYTHONUNBUFFERED True

# Copy local code to the container image.
ENV APP_HOME /app
WORKDIR $APP_HOME
COPY . ./

# Install production dependencies.
# We upgrade pip first to ensure we get the best binary wheel resolution
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Run the web service on container startup.
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 main:app
