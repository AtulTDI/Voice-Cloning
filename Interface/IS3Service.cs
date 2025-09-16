using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace AbhiyanAI.VideoWorkerService.Interface
{
    public interface IS3Service
    {
        bool UploadFile(string filePath, string applicationName, Guid userID, string campaignName);
    }
}
