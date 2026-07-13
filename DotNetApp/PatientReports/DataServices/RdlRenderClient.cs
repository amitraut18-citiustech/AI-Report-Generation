using System.Text;
using System.Text.Json;

namespace PatientReports.DataServices;

// Calls the RdlRenderService side-process (.NET Framework 4.8), which hosts the
// real ReportViewer RDL engine and renders the .rdl report definitions to PDF.
// See RdlRenderService/Program.cs for why this can't run in-process on .NET 8.
public class RdlRenderClient
{
    private readonly HttpClient _httpClient;
    private static readonly JsonSerializerOptions JsonOpts = new();

    public RdlRenderClient(HttpClient httpClient)
    {
        _httpClient = httpClient;
    }

    public async Task<byte[]> RenderAsync(string report, object rows, Dictionary<string, string>? parameters = null)
    {
        var payload = new { report, rows, parameters };
        var json = JsonSerializer.Serialize(payload, JsonOpts);

        using var content = new StringContent(json, Encoding.UTF8, "application/json");
        using var response = await _httpClient.PostAsync("render", content);

        if (!response.IsSuccessStatusCode)
        {
            var error = await response.Content.ReadAsStringAsync();
            throw new InvalidOperationException($"RdlRenderService returned {(int)response.StatusCode}: {error}");
        }

        return await response.Content.ReadAsByteArrayAsync();
    }
}
