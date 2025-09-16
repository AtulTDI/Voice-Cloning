# Base image with runtime only
FROM mcr.microsoft.com/dotnet/runtime:9.0 AS base
WORKDIR /app

# Build stage with SDK
FROM mcr.microsoft.com/dotnet/sdk:9.0 AS build
ARG BUILD_CONFIGURATION=Release
WORKDIR /src

# Copy project files
COPY ["AbhiyanAI.VideoWorkerService/AbhiyanAI.VideoWorkerService.csproj", "AbhiyanAI.VideoWorkerService/"]
COPY ["AbhiyanAI.Infrastructure/AbhiyanAI.Infrastructure.csproj", "AbhiyanAI.Infrastructure/"]
COPY ["AbhiyanAI.Shared/AbhiyanAI.Shared.csproj", "AbhiyanAI.Shared/"]
COPY ["AbhiyanAI/AbhiyanAIUserAuth.csproj", "AbhiyanAI/"]

# Restore dependencies
RUN dotnet restore "./AbhiyanAI.VideoWorkerService/AbhiyanAI.VideoWorkerService.csproj"

# Copy the rest of the source code
COPY . .

# Set working directory and build the project
WORKDIR "/src/AbhiyanAI.VideoWorkerService"
RUN dotnet build "./AbhiyanAI.VideoWorkerService.csproj" -c $BUILD_CONFIGURATION -o /app/build

# Publish stage
FROM build AS publish
ENV ASPNETCORE_ENVIRONMENT=Production
ARG BUILD_CONFIGURATION=Release
RUN dotnet publish "./AbhiyanAI.VideoWorkerService.csproj" -c $BUILD_CONFIGURATION -o /app/publish /p:UseAppHost=false

# Final runtime image
FROM base AS final
WORKDIR /app

# Install Python, pip, venv, and ffmpeg
RUN apt-get update && \
    apt-get install -y python3 python3-pip python3-venv ffmpeg libsndfile1 libgl1 libglib2.0-0 libsm6 libxrender1 libxext6 && \
    rm -rf /var/lib/apt/lists/*

# Copy the published .NET app
COPY --from=publish /app/publish .

# ✅ Copy Python backend and OpenVoice local code
COPY AbhiyanAI.VideoWorkerService/backend/ backend/
COPY AbhiyanAI.VideoWorkerService/openvoice/ backend/openvoice/

# ✅ Create virtual environment
RUN python3 -m venv /app/atul

RUN . /app/atul/bin/activate && \
    pip install --upgrade pip && \
    pip install pandas && \
    pip install -e backend/openvoice && \    
    pip install --no-cache-dir -r backend/requirements.txt
       

# ✅ Optional: create Logs folder
RUN mkdir -p /app/Logs

# Start the .NET application
ENTRYPOINT ["dotnet", "AbhiyanAI.VideoWorkerService.dll"]