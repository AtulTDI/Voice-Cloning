using AbhiyanAI.Infrastructure.Interface;
using AbhiyanAI.Infrastructure.Service;
using AbhiyanAI.Shared.Model; // Make sure this matches your actual namespace
using AbhiyanAI.VideoWorkerService;
using AbhiyanAI.VideoWorkerService.Interface;
using AbhiyanAI.VideoWorkerService.Services;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Configuration;
var host = Host.CreateDefaultBuilder(args)
    .ConfigureAppConfiguration((hostingContext, config) =>
    {
        config.AddEnvironmentVariables(); // 🧠 Read env vars like ConnectionStrings__DefaultConnection
    })
    .ConfigureServices((context, services) =>
    {
        var configuration = context.Configuration;

        services.AddDbContext<AppDbContext>(options =>
           options.UseNpgsql(configuration.GetConnectionString("DefaultConnection")));

        // Load AWS and custom services from shared Infrastructure
        services.AddInfrastructure(configuration);

        services.AddSingleton<IS3Uploader, S3Uploader>();

        services.AddHostedService<VideoProcessingService>();
    })
    .Build();

await host.RunAsync();

