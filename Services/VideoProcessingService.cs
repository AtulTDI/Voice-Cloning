using AbhiyanAI.Infrastructure.Interface;
using AbhiyanAI.Infrastructure.Service;
using AbhiyanAI.Shared.Enums;
using AbhiyanAI.Shared.Helper;
using AbhiyanAI.Shared.Model;
//using AbhiyanAIUserAuth.Hub;
using Amazon.Runtime.Internal;
//using Microsoft.AspNetCore.SignalR;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Internal;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;
using Newtonsoft.Json.Linq;
using RabbitMQ.Client;
using RabbitMQ.Client.Events;
using System;
using System.Collections.Concurrent;
using System.Diagnostics;
using System.IO;
using System.Text;
using System.Text.Json;
using static System.Runtime.InteropServices.JavaScript.JSType;

namespace AbhiyanAI.VideoWorkerService.Services
{
    public class VideoProcessingService : BackgroundService
    {
        private readonly ILogger<VideoProcessingService> _logger;
        private IConnection _connection;
        private IModel _channel;
        private readonly IServiceProvider _services;
        private readonly IConfiguration _configuration;
        private static readonly ConcurrentDictionary<string, StreamWriter> _writers = new();
        private readonly IS3Uploader _uploader;
        //private readonly IHubContext<VideoProgressHub> _hubContext;
        private string s3BucketName;
        //private string s3Key;
        public VideoProcessingService(ILogger<VideoProcessingService> logger, IConfiguration configuration,
            IServiceProvider services, IS3Uploader uploader)
        {
            _logger = logger;
            _configuration = configuration;
            _services = services;
            _uploader = uploader;
            //_hubContext = hubContext;
            InitRabbitMQ();
        }

        private bool InitRabbitMQ()
        {
            int retry = 0;
            while (retry < 10)
            {
                try
                {
                    string hostName = _configuration.GetValue<string>("RabbitMQ:Host") ?? "localhost";
                    var factory = new ConnectionFactory()
                    {
                        HostName = hostName
                    };
                    _logger.LogInformation($"RabbitMQ Host: {hostName}");
                    _connection = factory.CreateConnection();
                    _channel = _connection.CreateModel();
                    ushort count = ushort.Parse($"{_configuration["RabbitMQ:ParellelProcessCount"]}");
                    _channel.QueueDeclare("video-status-update", durable: true, exclusive: false, autoDelete: false);
                    // Add priority argument for video-processing queue
                    var args = new Dictionary<string, object>
                    {
                        { "x-max-priority", 10 }
                    };

                    _channel.QueueDeclare(
                        queue: "video-processing",
                        durable: true,
                        exclusive: false,
                        autoDelete: false,
                        arguments: args);
                    //_channel.QueueDeclare("video-processing", durable: true, exclusive: false, autoDelete: false);
                    _channel.BasicQos(0, count, false); // Allow up to 10 unacknowledged messages
                    return true; // success

                }
                catch (Exception)
                {
                    retry++;
                    Console.WriteLine($"RabbitMQ not ready. Retrying in 5 seconds... ({retry}/10)");
                    Thread.Sleep(5000);
                }
            }
            return false;
        }

        protected override Task ExecuteAsync(CancellationToken stoppingToken)
        {
            // Ensure RabbitMQ is connected before trying to consume
            if (!InitRabbitMQ())
            {
                Console.WriteLine("RabbitMQ connection failed after retries. Exiting worker.");
                return Task.CompletedTask; // or Environment.Exit(1);
            }
            var consumer = new EventingBasicConsumer(_channel);

            consumer.Received += async (model, ea) =>
            {
                var body = ea.Body.ToArray();
                var message = Encoding.UTF8.GetString(body);

                var jsonObj = JObject.Parse(message);

                // Remove or mask the sensitive field
                if (jsonObj["VideoCountKey"] != null)
                {
                    jsonObj["VideoCountKey"] = "***REDACTED***";
                }
                _logger.LogInformation($"[x] Received message: {jsonObj}");
                try
                {
                    var request = JsonSerializer.Deserialize<VideoRequest>(message);
                    if (request != null)
                    {
                        PublishStatusUpdate(request.RecepientID.ToString(), request.CustomizedVideoId, VideoStatus.Processing,"");
                        await Task.Run(() => ProcessVideoAsync(request, ea.DeliveryTag)); // Run concurrently
                    }
                    else
                    {
                        _logger.LogWarning("⚠️ Malformed message.");
                        _channel.BasicNack(ea.DeliveryTag, false, false); // Reject, do not requeue

                    }
                }
                catch (Exception ex)
                {
                    _logger.LogError(ex, $"❌ Exception: {ex.Message}");
                    _channel.BasicNack(ea.DeliveryTag, false, true); // Requeue for retry
                }
            };

            _channel.BasicConsume(queue: "video-processing", autoAck: false, consumer: consumer);
            return Task.CompletedTask;
        }

        private async Task ProcessVideoAsync(VideoRequest request, ulong deliveryTag)
        {
            using (var scope = _services.CreateScope())
            {
                var db = scope.ServiceProvider.GetRequiredService<AppDbContext>();
                // Example usage:
                CustomizedAIVideo? video = null;
                if (!string.Equals(request.CampaignName, "Sample", StringComparison.OrdinalIgnoreCase))
                {
                    video = await db.CustomizedAIVideos
                       .FirstOrDefaultAsync(v => v.Id == request.CustomizedVideoId);
                    if (video == null)
                    {
                        _logger.LogWarning($"Video with ID {request.CustomizedVideoId} not found.");
                        PublishStatusUpdate(request.RecepientID.ToString(), request.CustomizedVideoId, VideoStatus.Failed, "");
                        return;
                    }
                }

                try
                {
                    PublishStatusUpdate(request.RecepientID.ToString(), request.CustomizedVideoId, VideoStatus.Processing, "");
                    s3BucketName = _configuration["AWS:BucketName"];
                    var fileName = Path.GetFileName(request.BaseVideoUrl);
                    string safeTimestamp = DateTime.Now.ToString("yyyyMMdd_HHmmss");
                    var basevideolocalPath = Path.Combine("templates", $"{request.RecipientName}_{safeTimestamp}", fileName);
                    var basevideoDirectory = Path.Combine("templates", request.RecipientName);
                    if (!Directory.Exists(basevideoDirectory))
                    {
                        Directory.CreateDirectory(basevideoDirectory);
                    }
                    if (!File.Exists(basevideolocalPath))
                    {
                        await _uploader.DownloadFileAsync(s3BucketName, request.BaseVideoKey, basevideolocalPath);
                    }
                    PublishStatusUpdate(request.RecepientID.ToString(), request.CustomizedVideoId, VideoStatus.Processing, "");
                    //string basevideolocalPath = $"{"templates"}\"{Path.GetFileName(request.BaseVideoUrl)}";
                    _logger.LogInformation($"🚀 Start processing for user {request.UserId}, video: {request.BaseVideoUrl}");

                    if (video != null)
                    {
                        video.Status = VideoStatus.Processing;
                        await db.SaveChangesAsync();
                    }
                    await RunPythonScriptAsync(request, video, db, basevideolocalPath);
                    _logger.LogInformation($"✅ Completed processing for user {request.UserId}");
                    PublishStatusUpdate(request.RecepientID.ToString(), request.CustomizedVideoId, VideoStatus.Completed, "");
                    // ✅ Acknowledge message after processing
                    _channel.BasicAck(deliveryTag, false);
                }
                catch (Exception ex)
                {
                    if (video != null)
                    {
                        video.Status = VideoStatus.Failed;
                        video.ErrorMessage = ex.Message;
                    }
                    await db.SaveChangesAsync();
                    _logger.LogError(ex, $"❌ Failed to process video for {request.UserId}");
                    _channel.BasicNack(deliveryTag, false, true); // Requeue
                }
            }
        }

        private async Task RunPythonScriptAsync(VideoRequest request, CustomizedAIVideo? video, AppDbContext db, string basevideolocalPath)
        {
            PublishStatusUpdate(request.RecepientID.ToString(), request.CustomizedVideoId, VideoStatus.Processing, "");
            string userName = request.RecipientName;
            string safeName = userName.Replace(" ", "_");
            string pythonExe;
            string scriptPath;// = "backend/generate.py";
            if (OperatingSystem.IsWindows())
            {
                pythonExe = @"abhiyanai_env\Scripts\python.exe"; // Adjust if needed
                scriptPath = "backend/generate.py";
            }
            else
            {
                pythonExe = "/app/abhiyanai_env/bin/python"; // Correct venv path inside Docker
                scriptPath = "/app/backend/generate.py";
            }
            
            //string pythonExe = @"atul\Scripts\python.exe"; // Directly using Python, skip activate
            string argument = $"\"{scriptPath}\" \"{userName}\" \"{basevideolocalPath}\"";

            string logDir = "Logs";
            var uniqueId = Guid.NewGuid().ToString("N");
            string logFile = Path.Combine(logDir, $"VideoLog_{safeName}_{DateTime.UtcNow:yyyyMMddHHmmss}_{uniqueId}.log");
            Directory.CreateDirectory(logDir);

            var process = new Process
            {
                StartInfo = new ProcessStartInfo
                {
                    FileName = pythonExe,
                    Arguments = argument,
                    RedirectStandardOutput = true,
                    RedirectStandardError = true,
                    UseShellExecute = false,
                    CreateNoWindow = true
                }
            };

            var outputLines = new List<string>();
            var errorLines = new List<string>();

            using var logWriter = new StreamWriter(logFile, append: true, encoding: Encoding.UTF8)
            {
                AutoFlush = true
            };
            string finalVideoPath = null;
            process.OutputDataReceived += (sender, args) =>
            {
                if (!string.IsNullOrEmpty(args.Data))
                {
                    outputLines.Add(args.Data);
                    // Detect final .mp4 path
                    if (args.Data.EndsWith(".mp4", StringComparison.OrdinalIgnoreCase))
                    {
                        finalVideoPath = args.Data.Trim();
                    }
                    lock (logWriter)
                        logWriter.WriteLine($"[OUT] {args.Data}");
                }
            };

            process.ErrorDataReceived += (sender, args) =>
            {
                if (!string.IsNullOrEmpty(args.Data))
                {
                    errorLines.Add(args.Data);
                    lock (logWriter)
                        logWriter.WriteLine($"[ERR] {args.Data}");
                }
            };
            PublishStatusUpdate(request.RecepientID.ToString(), request.CustomizedVideoId, VideoStatus.Processing, "");
            process.Start();
            process.BeginOutputReadLine();
            process.BeginErrorReadLine();
            await process.WaitForExitAsync();

            // === ✅ Check for success ===
            if (process.ExitCode == 0)
            {
                string generatedVideoPath = Path.Combine("generated_videos", $"{safeName}.mp4");
                if (File.Exists(finalVideoPath))
                {
                    lock (logWriter)
                        logWriter.WriteLine($"[INFO] ✅ Video generated at: {finalVideoPath}");
                    string s3Key = GenerateS3Key(finalVideoPath, request.UserId, request.CampaignName, request.ApplicatioName);
                    using var fileStream = File.OpenRead(finalVideoPath);
                    await _uploader.UploadAsync(s3BucketName, s3Key, fileStream);
                    if (video != null)
                    {
                        video.Status = VideoStatus.Completed;
                        video.S3Key = s3Key;
                        string serviceUrl = _configuration["AWS:ServiceURL"];
                        video.S3Url = $"{serviceUrl}/{s3Key}";

                        //File.Delete(generatedVideoPath);

                        // Video count decrement 
                        var application = await db.Applications
                            .FirstOrDefaultAsync(a => a.Id == request.ApplicationId);

                        var success = await DecrementVideoCountAsync(db, application.Id, request.VideoCountKey);
                        PublishStatusUpdate(request.RecepientID.ToString(), request.CustomizedVideoId, VideoStatus.Completed, "");
                    }
                    else
                    {
                        string s3SingedURL = _uploader.GetSignedUrl(s3BucketName, s3Key);
                        PublishStatusUpdate(request.RecepientID.ToString(), request.CustomizedVideoId, VideoStatus.Completed, s3SingedURL);
                    }


                }
                else
                {
                    lock (logWriter)
                        logWriter.WriteLine($"[ERR] ❌ Script ran but video not found at expected path: {generatedVideoPath}{Environment.NewLine}");
                    if (video != null)
                        video.Status = VideoStatus.Failed;
                    PublishStatusUpdate(request.RecepientID.ToString(), request.CustomizedVideoId, VideoStatus.Failed, "");
                }
            }
            else
            {
                lock (logWriter)
                    logWriter.WriteLine($"[ERR] ❌ Script failed with exit code: {process.ExitCode}{Environment.NewLine}");
                if (errorLines.Any())
                {
                    lock (logWriter)
                        logWriter.WriteLine($"[ERR] Last Error: {errorLines.Last()}{Environment.NewLine}");
                    File.AppendAllText(logFile, $"[ERR] Last Error: {errorLines.Last()}{Environment.NewLine}");
                }

                if (video != null)
                    video.Status = VideoStatus.Failed;

                PublishStatusUpdate(request.RecepientID.ToString(), request.CustomizedVideoId, VideoStatus.Failed, "");
            }
            if (video != null)
                await db.SaveChangesAsync();
            File.Delete(basevideolocalPath);
        }

        public async Task<bool> DecrementVideoCountAsync(AppDbContext db, Guid appId, string secretKey)
        {
            await using var transaction = await db.Database.BeginTransactionAsync();

            // Lock the row for this AppId. Other processes will wait here until this transaction completes.
            var application = await db.Applications
    .FromSqlRaw(@"SELECT * FROM abhiyanai.""Applications"" WHERE ""Id"" = {0} FOR UPDATE", appId)
    .FirstOrDefaultAsync();

            if (application == null)
            {
                await transaction.RollbackAsync();
                return false;
            }

            // Decrypt and decrement
            string encrypted = application.RemainingCountEncrypted;
            if (!VideoCountCrypto.DecrementCount(ref encrypted, secretKey, application.Id, out long remaining))
            {
                // No credits left
                await transaction.RollbackAsync();
                return false;
            }

            application.RemainingCountEncrypted = encrypted;

            await db.SaveChangesAsync();
            await transaction.CommitAsync();

            return true;
        }

        public string GenerateS3Key(string filePath, Guid userID, string campaignName, string applicationName)
        {
            string extension = Path.GetExtension(filePath);
            string originalFileName = Path.GetFileNameWithoutExtension(filePath).Replace(" ", "_");
            string applicationNameSanitized = applicationName.Replace(" ", "_");
           // string timestamp = DateTime.UtcNow.ToString("yyyyMMddHHmmss");
            //var bucketName = _configuration["AWS:BucketName"];
            string userIDSanitized = userID.ToString(); // assuming Guid or string
            string campaignNameSanitized = campaignName.Replace(" ", "_");
            return $"{applicationNameSanitized}/{userIDSanitized}/{campaignNameSanitized}/{"Customized_AI_Videos"}/{originalFileName}{extension}";
        }

        private void PublishStatusUpdate(string recepientId, Guid customizedVideoId, VideoStatus status, string s3Link)
        {
            var update = new
            {
                RecepientID = recepientId,
                Status = status.ToString(),
                CustomizedVideoID = customizedVideoId,
                CustomizedVideoLink = s3Link
            };

            var json = JsonSerializer.Serialize(update);
            var body = Encoding.UTF8.GetBytes(json);

            _channel.BasicPublish(
                exchange: "",
                routingKey: "video-status-update",
                basicProperties: null,
                body: body
            );
        }

        public override void Dispose()
        {
            _channel?.Close();
            _connection?.Close();
            base.Dispose();
        }
    }
}