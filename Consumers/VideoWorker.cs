using AbhiyanAI.VideoWorkerService.Models;
using RabbitMQ.Client;
using RabbitMQ.Client.Events;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;

namespace AbhiyanAI.VideoWorkerService.Consumers
{
    public class VideoWorker : BackgroundService
    {
        private readonly ILogger<VideoWorker> _logger;

        public VideoWorker(ILogger<VideoWorker> logger)
        {
            _logger = logger;
        }

        protected override Task ExecuteAsync(CancellationToken stoppingToken)
        {
            var factory = new ConnectionFactory() { HostName = "localhost" };
            using var connection = factory.CreateConnection();
            using var channel = connection.CreateModel();

            channel.QueueDeclare(queue: "video_jobs", durable: false, exclusive: false, autoDelete: false, arguments: null);

            var consumer = new EventingBasicConsumer(channel);

            consumer.Received += async (model, ea) =>
            {
                var body = ea.Body.ToArray();
                var json = Encoding.UTF8.GetString(body);
                var job = JsonSerializer.Deserialize<VideoJob>(json);

                _logger.LogInformation($"[x] Received video job for {job.RecipientName}");

                // TODO: Call Python script, generate video, upload to S3, store DB record
            };

            channel.BasicConsume(queue: "video_jobs", autoAck: true, consumer: consumer);

            return Task.CompletedTask;
        }


    }
}
