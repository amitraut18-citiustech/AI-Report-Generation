using System;
using System.IO;
using System.Net;
using System.Text;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;

namespace RdlRenderService
{
    public class Program
    {
        public static void Main(string[] args)
        {
            var prefix = args.Length > 0 ? args[0] : "http://localhost:5250/";
            if (!prefix.EndsWith("/")) prefix += "/";

            var listener = new HttpListener();
            listener.Prefixes.Add(prefix);
            listener.Start();
            Console.WriteLine("RdlRenderService listening on " + prefix + " (POST /render). Ctrl+C to stop.");

            while (true)
            {
                var context = listener.GetContext();
                System.Threading.ThreadPool.QueueUserWorkItem(_ => HandleRequest(context));
            }
        }

        private static void HandleRequest(HttpListenerContext context)
        {
            var request = context.Request;
            var response = context.Response;
            try
            {
                if (request.HttpMethod != "POST" || request.Url.AbsolutePath.TrimEnd('/') != "/render")
                {
                    WriteError(response, 404, "Not found. POST JSON to /render.");
                    return;
                }

                string body;
                using (var reader = new StreamReader(request.InputStream, request.ContentEncoding ?? Encoding.UTF8))
                {
                    body = reader.ReadToEnd();
                }

                var json = JObject.Parse(body);
                var report = (string)json["report"];
                var rows = (JArray)json["rows"] ?? new JArray();
                var parameters = json["parameters"]?.ToObject<System.Collections.Generic.Dictionary<string, string>>();

                if (string.IsNullOrWhiteSpace(report))
                {
                    WriteError(response, 400, "Missing 'report'.");
                    return;
                }

                var pdfBytes = RdlRenderer.Render(report, rows, parameters);

                response.StatusCode = 200;
                response.ContentType = "application/pdf";
                response.ContentLength64 = pdfBytes.Length;
                response.OutputStream.Write(pdfBytes, 0, pdfBytes.Length);
                response.OutputStream.Close();
            }
            catch (ArgumentException ex)
            {
                Console.WriteLine("Bad request: " + ex.Message);
                WriteError(response, 400, ex.Message);
            }
            catch (Exception ex)
            {
                Console.WriteLine("Render failed: " + ex);
                WriteError(response, 500, ex.ToString());
            }
        }

        private static void WriteError(HttpListenerResponse response, int statusCode, string message)
        {
            response.StatusCode = statusCode;
            response.ContentType = "application/json";
            var payload = Encoding.UTF8.GetBytes(JsonConvert.SerializeObject(new { error = message }));
            response.ContentLength64 = payload.Length;
            response.OutputStream.Write(payload, 0, payload.Length);
            response.OutputStream.Close();
        }
    }
}
