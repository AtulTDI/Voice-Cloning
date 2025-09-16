using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace AbhiyanAI.VideoWorkerService.Models
{
    public class VideoJob
    {
        public Guid UserId { get; set; }
        public string BaseVideoUrl { get; set; }
        public string CampaignName { get; set; }
        public string RecipientName { get; set; }
        public string OutputFileName { get; set; }
    }
}
