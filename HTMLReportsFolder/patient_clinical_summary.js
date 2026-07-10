(function () {
  "use strict";

  // ---------------------------------------------------------------------------
  // Patient Clinical Summary Report
  //
  // Source of truth: ReportThoughts/patient_clinical_summary.thought.md
  // The RDL is authoritative wherever the RDL and the .NET service diverge.
  //
  // window.REPORT_DATA.rows is the FLAT joined result set: one row per lab
  // result, with event/patient/facility metadata repeated; a row with null lab
  // columns represents an event that has no labs (LEFT JOIN). All grouping and
  // aggregation is performed here in JS.
  // ---------------------------------------------------------------------------

  function getData() {
    return window.REPORT_DATA || { parameters: {}, rows: [], narrative: "", meta: {} };
  }

  // ---- value helpers --------------------------------------------------------

  function isNil(v) {
    return v === null || v === undefined || v === "";
  }

  // Accepts real booleans, "Yes"/"No", "true"/"false", 1/0.
  function isTrue(v) {
    if (v === true) return true;
    if (typeof v === "number") return v === 1;
    if (typeof v === "string") {
      var s = v.trim().toLowerCase();
      return s === "true" || s === "yes" || s === "y" || s === "1";
    }
    return false;
  }

  function toNumber(v) {
    if (isNil(v)) return null;
    var n = typeof v === "number" ? v : parseFloat(v);
    return isNaN(n) ? null : n;
  }

  function parseDate(v) {
    if (isNil(v)) return null;
    var d = v instanceof Date ? v : new Date(v);
    return isNaN(d.getTime()) ? null : d;
  }

  function pad2(n) { return (n < 10 ? "0" : "") + n; }

  // Match RDL Format(date, "MM/dd/yyyy").
  function formatDate(v) {
    var d = parseDate(v);
    if (!d) return "";
    return pad2(d.getMonth() + 1) + "/" + pad2(d.getDate()) + "/" + d.getFullYear();
  }

  // Match RDL Format(ExecutionTime, "MM/dd/yyyy HH:mm").
  function formatDateTime(v) {
    var d = parseDate(v);
    if (!d) return "";
    return formatDate(d) + " " + pad2(d.getHours()) + ":" + pad2(d.getMinutes());
  }

  // ---- calculated fields (RDL <Field> expressions) --------------------------

  // Age = Floor(DateDiff(Day, DOB, Today()) / 365.25)   (RDL, authoritative)
  function computeAge(dateOfBirth) {
    var dob = parseDate(dateOfBirth);
    if (!dob) return null;
    var days = Math.floor((Date.now() - dob.getTime()) / 86400000);
    return Math.floor(days / 365.25);
  }

  // BMI = IIF(HeightCm > 0, Round(WeightKg / (HeightCm/100)^2, 1), 0)
  function computeBmi(heightCm, weightKg) {
    var h = toNumber(heightCm);
    var w = toNumber(weightKg);
    if (h === null || w === null || h <= 0) return 0;
    var m = h / 100;
    return Math.round((w / (m * m)) * 10) / 10;
  }

  // DaysSincePreviousVisit = DateDiff(Day, DateOfPreviousVisit, DateOfVisit)
  function computeDaysSincePreviousVisit(dateOfPreviousVisit, dateOfVisit) {
    var prev = parseDate(dateOfPreviousVisit);
    var cur = parseDate(dateOfVisit);
    if (!prev || !cur) return null;
    return Math.round((cur.getTime() - prev.getTime()) / 86400000);
  }

  // LabFlag = "" if no value; "OUT" if value < RefLow or > RefHigh; else "OK".
  function computeLabFlag(labValue, refLow, refHigh) {
    var v = toNumber(labValue);
    if (v === null) return "";
    var lo = toNumber(refLow);
    var hi = toNumber(refHigh);
    if ((lo !== null && v < lo) || (hi !== null && v > hi)) return "OUT";
    return "OK";
  }

  // ---- custom VB <Code> functions (exact thresholds from the thought file) --

  function bmiCategory(bmi) {
    if (bmi === 0) return "N/A";
    if (bmi < 18.5) return "Underweight";
    if (bmi < 25) return "Normal";
    if (bmi < 30) return "Overweight";
    return "Obese";
  }

  function riskScore(age, inpatient, outOfRangeLabs) {
    var score = 0;
    if (age >= 65) score += 2;
    else if (age >= 45) score += 1;
    if (inpatient) score += 2;
    score += outOfRangeLabs;
    return score;
  }

  var HIGH_RISK_THRESHOLD = 4;

  // ---- RDL WHERE clause (the injecting .NET service does NOT filter) ---------
  // te.DateOfVisit BETWEEN @FromDate AND @ToDate AND (@Status='All' OR p.Status=@Status)
  function applyRdlFilter(rows, params) {
    var from = parseDate(params.fromDate);
    var to = parseDate(params.toDate);
    var status = params.status;
    return rows.filter(function (r) {
      var visit = parseDate(r.dateOfVisit);
      if (from && visit && visit < from) return false;
      if (to && visit && visit > to) return false;
      if (status && status !== "All" && r.status !== status) return false;
      return true;
    });
  }

  // ---- grouping: Facility -> Patient -> (Event, Lab) detail rows -------------
  // Dataset ORDER BY f.Name, p.LastName, te.DateOfVisit, lr.TestName. We sort
  // facilities by FacilityName, patients by PatientName (grpPatient sort), and
  // detail rows by DateOfVisit then LabTestName (grpDetail sort).
  function groupByFacility(rows) {
    var facMap = {};
    var facOrder = [];

    rows.forEach(function (r) {
      var age = computeAge(r.dateOfBirth);
      var bmi = computeBmi(r.heightCm, r.weightKg);
      var flag = computeLabFlag(r.labValue, r.refLow, r.refHigh);
      var enriched = {
        row: r,
        age: age,
        bmi: bmi,
        labFlag: flag,
        inpatient: isTrue(r.isInpatient),
        daysSincePreviousVisit: computeDaysSincePreviousVisit(r.dateOfPreviousVisit, r.dateOfVisit)
      };

      var fName = r.facilityName || "";
      if (!facMap[fName]) {
        facMap[fName] = {
          facilityName: fName,
          facilityCity: r.facilityCity || "",
          facilityState: r.facilityState || "",
          patientMap: {},
          patientOrder: [],
          allEnriched: []
        };
        facOrder.push(fName);
      }
      var fac = facMap[fName];
      fac.allEnriched.push(enriched);

      var pKey = String(r.patientId);
      if (!fac.patientMap[pKey]) {
        fac.patientMap[pKey] = {
          patientId: r.patientId,
          patientName: r.patientName || "",
          mrn: r.mrn || "",
          gender: r.gender || "",
          age: age,
          bmi: bmi,
          primaryDiagnosis: r.primaryDiagnosis || "",
          activeMedCount: isNil(r.activeMedCount) ? 0 : r.activeMedCount,
          details: []
        };
        fac.patientOrder.push(pKey);
      }
      fac.patientMap[pKey].details.push(enriched);
    });

    return facOrder.map(function (fName) {
      var fac = facMap[fName];

      var patients = fac.patientOrder.map(function (pKey) {
        var p = fac.patientMap[pKey];

        // detail sort: DateOfVisit, then LabTestName
        p.details.sort(function (a, b) {
          var da = parseDate(a.row.dateOfVisit), db = parseDate(b.row.dateOfVisit);
          var ta = da ? da.getTime() : 0, tb = db ? db.getTime() : 0;
          if (ta !== tb) return ta - tb;
          var la = (a.row.labTestName || "").toLowerCase();
          var lb = (b.row.labTestName || "").toLowerCase();
          return la < lb ? -1 : la > lb ? 1 : 0;
        });

        // Patient-scoped risk: age, ANY inpatient event, total OUT labs.
        var anyInpatient = p.details.some(function (d) { return d.inpatient; });
        var outCount = p.details.reduce(function (n, d) {
          return n + (d.labFlag === "OUT" ? 1 : 0);
        }, 0);
        var risk = riskScore(p.age || 0, anyInpatient, outCount);

        p.riskScore = risk;
        p.isHighRisk = risk >= HIGH_RISK_THRESHOLD;
        p.bmiCategory = bmiCategory(p.bmi);
        return p;
      }).sort(function (a, b) {
        return a.patientName.toLowerCase() < b.patientName.toLowerCase() ? -1
             : a.patientName.toLowerCase() > b.patientName.toLowerCase() ? 1 : 0;
      });

      return { facility: fac, patients: patients };
    }).sort(function (a, b) {
      return a.facility.facilityName.toLowerCase() < b.facility.facilityName.toLowerCase() ? -1
           : a.facility.facilityName.toLowerCase() > b.facility.facilityName.toLowerCase() ? 1 : 0;
    });
  }

  // ---- Facility Summary aggregates (grpFacSummary scope) ---------------------
  function summarizeFacility(fac) {
    var rows = fac.allEnriched;
    var patientIds = {}, eventIds = {}, inpatientEventIds = {};
    var ageSum = 0, ageCount = 0, oorLabs = 0;

    rows.forEach(function (d) {
      var r = d.row;
      patientIds[String(r.patientId)] = true;
      if (!isNil(r.eventId)) eventIds[String(r.eventId)] = true;
      // SSRS Avg(Age) over the facility's rows (row-weighted, not per patient).
      if (d.age !== null) { ageSum += d.age; ageCount += 1; }
      if (d.inpatient && !isNil(r.eventId)) inpatientEventIds[String(r.eventId)] = true;
      if (d.labFlag === "OUT") oorLabs += 1;
    });

    return {
      facilityName: fac.facilityName,
      patientCount: Object.keys(patientIds).length,
      eventCount: Object.keys(eventIds).length,
      avgAge: ageCount ? Math.round(ageSum / ageCount) : 0,
      inpatientEvents: Object.keys(inpatientEventIds).length,
      oorLabs: oorLabs
    };
  }

  // ---- rendering ------------------------------------------------------------

  function renderFilters(el, params) {
    if (!el) return;
    // RDL: "Filters  -  Visit dates: {from} to {to}     |     Patient status: {status}"
    var from = formatDate(params.fromDate) || "(any)";
    var to = formatDate(params.toDate) || "(any)";
    var status = params.status || "All";
    el.textContent = "Filters  -  Visit dates: " + from + " to " + to +
      "     |     Patient status: " + status;
  }

  function renderNarrative(el, text) {
    if (!el) return;
    if (text && String(text).trim()) {
      el.textContent = text;
      el.hidden = false;
    } else {
      el.hidden = true;
    }
  }

  function cell(text, opts) {
    var td = document.createElement("td");
    td.textContent = isNil(text) ? "" : String(text);
    if (opts && opts.className) td.className = opts.className;
    if (opts && opts.colspan) td.colSpan = opts.colspan;
    return td;
  }

  function renderFacilitySummary(tbody, groups) {
    if (!tbody) return;
    tbody.textContent = "";
    groups.forEach(function (g) {
      var s = summarizeFacility(g.facility);
      var tr = document.createElement("tr");
      tr.appendChild(cell(s.facilityName));
      tr.appendChild(cell(s.patientCount, { className: "num" }));
      tr.appendChild(cell(s.eventCount, { className: "num" }));
      tr.appendChild(cell(s.avgAge, { className: "num" }));
      tr.appendChild(cell(s.inpatientEvents, { className: "num" }));
      // Conditional: out-of-range > 0 -> red + bold.
      tr.appendChild(cell(s.oorLabs, { className: s.oorLabs > 0 ? "num oor-hit" : "num" }));
      tbody.appendChild(tr);
    });
  }

  function facilityBandRow(fac) {
    var tr = document.createElement("tr");
    tr.className = "facility-band";
    var label = "Facility:  " + fac.facilityName + "   -   " +
      fac.facilityCity + ", " + fac.facilityState;
    tr.appendChild(cell(label, { colspan: 9 }));
    return tr;
  }

  function patientBannerRow(p) {
    var tr = document.createElement("tr");
    tr.className = "patient-banner " + (p.isHighRisk ? "risk-high" : "risk-low");
    var td = document.createElement("td");
    td.colSpan = 9;

    var bmiText = p.bmi ? (p.bmi + " (" + p.bmiCategory + ")") : ("0 (" + p.bmiCategory + ")");
    var parts = [
      p.patientName,
      "MRN: " + p.mrn,
      "Age: " + (p.age === null ? "-" : p.age),
      "Sex: " + (p.gender || "-"),
      "BMI: " + bmiText,
      "Dx: " + (p.primaryDiagnosis || "-"),
      "Active meds: " + p.activeMedCount
    ];
    td.appendChild(document.createTextNode(parts.join("   |   ") + "   "));

    var pill = document.createElement("span");
    pill.className = "risk-pill";
    pill.textContent = "Risk: " + p.riskScore + (p.isHighRisk ? " (HIGH)" : "");
    td.appendChild(pill);

    tr.appendChild(td);
    return tr;
  }

  function detailRow(d) {
    var r = d.row;
    var tr = document.createElement("tr");

    tr.appendChild(cell(r.eventId));                               // Event

    // Visit Date + Days-since-previous-visit sub-note (see .md deviation note).
    var visitTd = cell(formatDate(r.dateOfVisit));
    if (d.daysSincePreviousVisit !== null) {
      var note = document.createElement("span");
      note.className = "visit-subnote";
      note.textContent = d.daysSincePreviousVisit + " days since prior visit";
      visitTd.appendChild(note);
    }
    tr.appendChild(visitTd);

    var provider = (r.providerName || "") + (r.specialty ? " (" + r.specialty + ")" : "");
    tr.appendChild(cell(provider));                                // Provider
    tr.appendChild(cell(r.donorType));                             // Donor

    // Setting: Inpatient/Outpatient, yellow highlight when inpatient.
    tr.appendChild(cell(d.inpatient ? "Inpatient" : "Outpatient",
      { className: d.inpatient ? "setting-inpatient" : "" }));     // Setting

    tr.appendChild(cell(isNil(r.labTestName) ? "-" : r.labTestName)); // Test

    // Result: value + unit, or "-".
    var result = isNil(r.labValue) ? "-" : (r.labValue + (r.labUnit ? " " + r.labUnit : ""));
    tr.appendChild(cell(result));                                  // Result

    // Reference: low - high, or "-".
    var reference = isNil(r.refLow) ? "-" : (r.refLow + " - " + r.refHigh);
    tr.appendChild(cell(reference));                               // Reference

    // Flag: OUT (red bold) / OK (green) / "".
    var flagClass = d.labFlag === "OUT" ? "flag-out" : (d.labFlag === "OK" ? "flag-ok" : "");
    tr.appendChild(cell(d.labFlag, { className: flagClass }));     // Flag

    return tr;
  }

  function renderDetail(tbody, groups) {
    if (!tbody) return;
    tbody.textContent = "";
    groups.forEach(function (g) {
      tbody.appendChild(facilityBandRow(g.facility));
      g.patients.forEach(function (p) {
        tbody.appendChild(patientBannerRow(p));
        p.details.forEach(function (d) {
          tbody.appendChild(detailRow(d));
        });
      });
    });
  }

  function renderFooter(data, params) {
    var gen = document.querySelector("[data-generated]");
    var page = document.querySelector("[data-pageinfo]");
    var meta = data.meta || {};
    if (gen) {
      var when = formatDateTime(meta.generatedAt);
      var runBy = params.rptUser || meta.executedBy || "system";
      gen.textContent = "Generated: " + (when || "-") + "     |     Run by: " + runBy;
    }
    // RDL "Page X of Y" is a paginated-render concept; not meaningful in a single
    // scrollable HTML page. Show row count instead.
    if (page) page.textContent = "Rows: " + (meta.rowCount != null ? meta.rowCount : "");
  }

  function toggleSections(hasData) {
    var summary = document.querySelector("[data-section-summary]");
    var detail = document.querySelector("[data-section-detail]");
    var empty = document.querySelector("[data-empty]");
    if (summary) summary.hidden = !hasData;
    if (detail) detail.hidden = !hasData;
    if (empty) empty.hidden = hasData;
  }

  document.addEventListener("DOMContentLoaded", function () {
    var data = getData();
    var params = data.parameters || {};
    var allRows = Array.isArray(data.rows) ? data.rows : [];

    renderFilters(document.querySelector("[data-filters]"), params);
    renderNarrative(document.querySelector("[data-narrative]"), data.narrative);

    // Reproduce the RDL WHERE clause (the injecting service loads unfiltered).
    var rows = applyRdlFilter(allRows, params);

    if (!rows.length) {
      toggleSections(false);
      renderFooter(data, params);
      return;
    }

    var groups = groupByFacility(rows);
    toggleSections(true);
    renderFacilitySummary(document.querySelector("[data-facility-summary]"), groups);
    renderDetail(document.querySelector("[data-detail]"), groups);
    renderFooter(data, params);
  });
})();
