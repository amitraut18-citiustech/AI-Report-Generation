namespace PatientReports.Models;

public class DecodeResult
{
    public string Report { get; set; } = "UNKNOWN";

    /// <summary>
    /// Structured query spec. The Python brain returns this as a nested
    /// "query" object containing entity, joins, and filters.
    /// </summary>
    public QuerySpec Query { get; set; } = new();

    /// <summary>
    /// Fallback: if the brain returns a flat "filters" array at the top
    /// level (older brain versions), capture it here so
    /// <see cref="NormalizeFilters"/> can merge it into <see cref="Query"/>.
    /// </summary>
    public List<QueryFilter> Filters { get; set; } = new();

    public Dictionary<string, object?> Parameters { get; set; } = new();
    public string? Template { get; set; }
    public double Confidence { get; set; }
    public string? Message { get; set; }

    /// <summary>
    /// Ensures <see cref="Query.Filters"/> is populated regardless of whether
    /// the brain returned filters inside "query" or at the top level.
    /// Also defaults any empty <see cref="QueryFilter.Table"/> to the given
    /// primary table name so the query service can route the filter.
    /// </summary>
    public void NormalizeFilters(string primaryTable)
    {
        // Merge top-level filters into Query if Query.Filters is empty.
        if (Filters.Count > 0 && Query.Filters.Count == 0)
            Query.Filters = Filters;

        // Default any filter with a missing/empty table to the primary table.
        foreach (var f in Query.Filters)
        {
            if (string.IsNullOrWhiteSpace(f.Table))
                f.Table = primaryTable;
        }
    }
}
