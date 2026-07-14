using System.Text;
using System.Text.Json;
using PatientReports.Models;

namespace PatientReports.DataServices;

public class ReportBrainClient
{
    private readonly HttpClient _httpClient;

    private static readonly JsonSerializerOptions JsonOpts = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
        PropertyNameCaseInsensitive = true
    };

    public ReportBrainClient(HttpClient httpClient)
    {
        _httpClient = httpClient;
    }

    public async Task<DecodeResult> DecodePromptAsync(string question, string provider = "local")
    {
        var payload = new { question, provider };
        var json = JsonSerializer.Serialize(payload, JsonOpts);

        using var content = new StringContent(json, Encoding.UTF8, "application/json");
        using var response = await _httpClient.PostAsync("decode-prompt", content);

        if (!response.IsSuccessStatusCode)
        {
            var error = await response.Content.ReadAsStringAsync();
            throw new InvalidOperationException(
                $"Brain /decode-prompt returned {(int)response.StatusCode}: {error}");
        }

        var body = await response.Content.ReadAsStringAsync();
        return JsonSerializer.Deserialize<DecodeResult>(body, JsonOpts)
               ?? new DecodeResult();
    }

    public async Task<PromptLogResponse> GetPromptLogAsync()
    {
        using var response = await _httpClient.GetAsync("prompt-log");

        if (!response.IsSuccessStatusCode)
        {
            var error = await response.Content.ReadAsStringAsync();
            throw new InvalidOperationException(
                $"Brain /prompt-log returned {(int)response.StatusCode}: {error}");
        }

        var body = await response.Content.ReadAsStringAsync();
        return JsonSerializer.Deserialize<PromptLogResponse>(body, JsonOpts)
               ?? new PromptLogResponse();
    }

    public async Task<SummarizeResult> SummarizeAsync(
        string question, object results, int rowCount, string table = "Patients")
    {
        var payload = new { question, results, row_count = rowCount, table };
        var json = JsonSerializer.Serialize(payload, JsonOpts);

        using var content = new StringContent(json, Encoding.UTF8, "application/json");
        using var response = await _httpClient.PostAsync("summarize", content);

        if (!response.IsSuccessStatusCode)
        {
            var error = await response.Content.ReadAsStringAsync();
            throw new InvalidOperationException(
                $"Brain /summarize returned {(int)response.StatusCode}: {error}");
        }

        var body = await response.Content.ReadAsStringAsync();
        return JsonSerializer.Deserialize<SummarizeResult>(body, JsonOpts)
               ?? new SummarizeResult();
    }
}
