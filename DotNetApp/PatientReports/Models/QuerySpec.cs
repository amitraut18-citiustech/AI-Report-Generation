namespace PatientReports.Models;

public class QuerySpec
{
    public string Entity { get; set; } = "";
    public List<JoinSpec> Joins { get; set; } = new();
    public List<QueryFilter> Filters { get; set; } = new();
}

public class JoinSpec
{
    public string Table { get; set; } = "";
    public string LocalKey { get; set; } = "";
    public string ForeignKey { get; set; } = "Id";
}

public class QueryFilter
{
    public string Table { get; set; } = "";
    public string Field { get; set; } = "";
    public string Operator { get; set; } = "equals";
    public string Value { get; set; } = "";
    public string Status { get; set; } = "pending";
}
