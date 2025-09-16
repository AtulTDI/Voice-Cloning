using Amazon;
using Amazon.S3;
using Amazon.S3.Model;
using Microsoft.Extensions.Configuration;
using System;
using System.IO;
using System.Threading.Tasks;

namespace AbhiyanAI.VideoWorkerService
{
    public class s3uploader
    {
        private readonly IConfiguration _configuration;
        //public s3uploader(IConfiguration configuration)
        //{
        //    _configuration = configuration;
        //}
        public async Task news3uploader(string filePath, string s3Key)
        {
            var region = _configuration["AWS:Region"] ?? "us-east-1";
            var accessKey = _configuration["AWS:AccessKey"] ?? "test";
            var secretKey = _configuration["AWS:SecretKey"] ?? "test";
            string bucketName = _configuration["AWS:BucketName"];

            var s3Client = new AmazonS3Client(accessKey, secretKey, RegionEndpoint.GetBySystemName(region));

            try
            {
                using var fileStream = new FileStream(filePath, FileMode.Open, FileAccess.Read);

                var putRequest = new PutObjectRequest
                {
                    BucketName = bucketName,
                    Key = s3Key,
                    InputStream = fileStream,
                    AutoCloseStream = true,
                    ContentType = "video/mp4"
                };

                var response = await s3Client.PutObjectAsync(putRequest);

                Console.WriteLine("✅ File uploaded successfully.");
            }
            catch (AmazonS3Exception ex)
            {
                Console.WriteLine($"❌ AWS error: {ex.Message}");
            }
            catch (Exception ex)
            {
                Console.WriteLine($"❌ General error: {ex.Message}");
            }
        }
    }
}
