namespace PatientReports.Models;

/// <summary>
/// One entry from the brain's /prompt-log endpoint: what was actually sent to
/// an LLM for a decode or summarize call. Backs the Prompt Log page that
/// showcases PHI anonymization (original vs. sent).
/// </summary>
public class PromptLogEntry
{
    public string? Timestamp { get; set; }

    /// <summary>"decode" or "summarize".</summary>
    public string? Kind { get; set; }

    /// <summary>Requested provider on decode calls ("local" / "claude").</summary>
    public string? Provider { get; set; }

    /// <summary>Model that actually answered a decode ("ollama" / "claude" / "claude_fallback").</summary>
    public string? Source { get; set; }

    /// <summary>Model used for a summarize call ("ollama" / "claude").</summary>
    public string? Model { get; set; }

    /// <summary>Whether the decode produced a usable result (decode entries only).</summary>
    public bool? Succeeded { get; set; }

    /// <summary>Whether a Claude fallback was attempted after a local failure (decode entries only).</summary>
    public bool? FallbackAttempted { get; set; }

    /// <summary>The question text as sent to the LLM (scrubbed on summarize).</summary>
    public string? SentQuestion { get; set; }

    /// <summary>The user's original question (summarize entries only).</summary>
    public string? OriginalQuestion { get; set; }

    public List<Dictionary<string, object?>>? OriginalRowsSample { get; set; }
    public List<Dictionary<string, object?>>? SentRowsSample { get; set; }

    public int? RowCount { get; set; }
    public string? Report { get; set; }
    public string? Note { get; set; }
}

public class PromptLogResponse
{
    public List<PromptLogEntry> Entries { get; set; } = new();
}

public class PromptLogViewModel
{
    public List<PromptLogEntry> Entries { get; set; } = new();
    public string? Error { get; set; }
}
