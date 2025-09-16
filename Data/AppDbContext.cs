using AbhiyanAI.Shared.Model;
using Microsoft.EntityFrameworkCore;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;


namespace AbhiyanAI.VideoWorkerService.Data
{
    public class AppDbContext : DbContext
    {

        public AppDbContext(DbContextOptions<AppDbContext> options) : base(options) { }

        //  public DbSet<CustomizedAIVideo> CustomizedAIVideos { get; set; }
        //public DbSet<VideoSendLog> VideoSendLogs { get; set; }
    }
}