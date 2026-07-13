(function () {
  "use strict";

  /* ------------------------------------------------------------------ */
  /*  Data access                                                        */
  /* ------------------------------------------------------------------ */

  function getData() {
    return window.REPORT_DATA || { parameters: {}, rows: [], narrative: "", meta: {} };
  }

  /* ------------------------------------------------------------------ */
  /*  Filter form: populate from applied parameters, reload on submit    */
  /* ------------------------------------------------------------------ */

  function wireFilterForm(params) {
    var form = document.querySelector("[data-filter-form]");
    if (!form) return;
    Object.keys(params || {}).forEach(function (k) {
      var el = form.querySelector('[name="' + k + '"]');
      if (el && params[k] != null) {
        var val = String(params[k]);
        if (el.type === "date" && val.indexOf("T") > -1) {
          val = val.split("T")[0];
        }
        el.value = val;
      }
    });
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      var qs = new URLSearchParams(location.search);
      form.querySelectorAll("[name]").forEach(function (el) {
        qs.set(el.name, el.value);
      });
      location.search = qs.toString();
    });
  }

  /* ------------------------------------------------------------------ */
  /*  Helpers                                                            */
  /* ------------------------------------------------------------------ */

  /** Parse an ISO date string into a local-time Date, avoiding UTC-midnight shifts. */
  function parseLocalDate(isoStr) {
    if (!isoStr) return null;
    var s = String(isoStr);
    var dp = s.indexOf("T") > -1 ? s.split("T")[0] : s;
    var p = dp.split("-");
    if (p.length !== 3) return null;
    return new Date(parseInt(p[0], 10), parseInt(p[1], 10) - 1, parseInt(p[2], 10));
  }

  /** Format an ISO date string as MM/dd/yyyy. */
  function formatDate(isoStr) {
    var d = parseLocalDate(isoStr);
    if (!d) return "-";
    var mm = String(d.getMonth() + 1).padStart(2, "0");
    var dd = String(d.getDate()).padStart(2, "0");
    return mm + "/" + dd + "/" + d.getFullYear();
  }

  /** Format an ISO datetime string as MM/dd/yyyy HH:mm (local time). */
  function formatDateTime(isoStr) {
    if (!isoStr) return "";
    var d = new Date(isoStr);
    if (isNaN(d.getTime())) return "";
    var mm = String(d.getMonth() + 1).padStart(2, "0");
    var dd = String(d.getDate()).padStart(2, "0");
    var hh = String(d.getHours()).padStart(2, "0");
    var mi = String(d.getMinutes()).padStart(2, "0");
    return mm + "/" + dd + "/" + d.getFullYear() + " " + hh + ":" + mi;
  }

  function escapeHtml(str) {
    if (str == null) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  /* ------------------------------------------------------------------ */
  /*  Calculated fields (computed from ClinicalFlatRow raw fields)       */
  /* ------------------------------------------------------------------ */

  /** Calendar-year age: today.year - dob.year, adjusted if birthday not yet reached. */
  function calculateAge(dobStr) {
    var dob = parseLocalDate(dobStr);
    if (!dob) return 0;
    var today = new Date();
    var age = today.getFullYear() - dob.getFullYear();
    var m = today.getMonth() - dob.getMonth();
    if (m < 0 || (m === 0 && today.getDate() < dob.getDate())) {
      age--;
    }
    return age;
  }

  /** BMI = weightKg / (heightCm/100)^2, rounded to 1 decimal; 0 if heightCm <= 0. */
  function calculateBmi(weightKg, heightCm) {
    if (!heightCm || heightCm <= 0) return 0;
    return Math.round((weightKg / Math.pow(heightCm / 100, 2)) * 10) / 10;
  }

  /** Categorical BMI label per RDL BmiCategory function. */
  function getBmiCategory(bmi) {
    if (bmi === 0) return "N/A";
    if (bmi < 18.5) return "Underweight";
    if (bmi < 25) return "Normal";
    if (bmi < 30) return "Overweight";
    return "Obese";
  }

  /** Lab status flag: "" if no lab, "OUT" if out of range, "OK" otherwise. */
  function getLabFlag(labValue, refLow, refHigh) {
    if (labValue == null) return "";
    if (labValue < refLow || labValue > refHigh) return "OUT";
    return "OK";
  }

  /* ------------------------------------------------------------------ */
  /*  Sorting (FacilityName, PatientName, DateOfVisit, LabTestName ASC)  */
  /* ------------------------------------------------------------------ */

  function sortRows(rows) {
    rows.sort(function (a, b) {
      var c = (a.facilityName || "").localeCompare(b.facilityName || "");
      if (c !== 0) return c;
      c = (a.patientName || "").localeCompare(b.patientName || "");
      if (c !== 0) return c;
      c = (a.dateOfVisit || "").localeCompare(b.dateOfVisit || "");
      if (c !== 0) return c;
      var la = a.labTestName || "￿";
      var lb = b.labTestName || "￿";
      return la.localeCompare(lb);
    });
  }

  /* ------------------------------------------------------------------ */
  /*  Risk score: per-patient aggregation                                */
  /*  +2 if age>=65, else +1 if age>=45; +2 if any inpatient event;     */
  /*  + count of out-of-range labs. Threshold for high-risk: >= 4.       */
  /* ------------------------------------------------------------------ */

  function computeRiskScores(rows) {
    var patients = {};

    rows.forEach(function (r) {
      var pid = r.patientId;
      if (!patients[pid]) {
        patients[pid] = { dob: r.dateOfBirth, hasInpatient: false, outOfRange: 0 };
      }
      if (r.isInpatient) patients[pid].hasInpatient = true;
      if (r.labValue != null && (r.labValue < r.refLow || r.labValue > r.refHigh)) {
        patients[pid].outOfRange++;
      }
    });

    var scores = {};
    Object.keys(patients).forEach(function (pid) {
      var p = patients[pid];
      var age = calculateAge(p.dob);
      var score = 0;
      if (age >= 65) score += 2;
      else if (age >= 45) score += 1;
      if (p.hasInpatient) score += 2;
      score += p.outOfRange;
      scores[pid] = score;
    });
    return scores;
  }

  /* ------------------------------------------------------------------ */
  /*  Facility Summary table                                             */
  /* ------------------------------------------------------------------ */

  function buildFacilitySummary(rows) {
    // Collect per-facility aggregates
    var facilities = {};
    var facilityOrder = [];

    rows.forEach(function (r) {
      var fn = r.facilityName || "";
      if (!facilities[fn]) {
        facilities[fn] = {
          patients: {},
          events: {},
          inpatientEvents: {},
          outOfRange: 0,
          ageSum: 0,
          rowCount: 0
        };
        facilityOrder.push(fn);
      }
      var f = facilities[fn];
      f.patients[r.patientId] = true;
      f.events[r.eventId] = true;
      if (r.isInpatient) f.inpatientEvents[r.eventId] = true;
      if (getLabFlag(r.labValue, r.refLow, r.refHigh) === "OUT") f.outOfRange++;
      f.ageSum += calculateAge(r.dateOfBirth);
      f.rowCount++;
    });

    facilityOrder.sort();

    var tbody = document.querySelector("[data-facility-summary]");
    if (!tbody) return;

    facilityOrder.forEach(function (fn) {
      var f = facilities[fn];
      var patientCount = Object.keys(f.patients).length;
      var eventCount = Object.keys(f.events).length;
      var inpatientCount = Object.keys(f.inpatientEvents).length;
      var avgAge = f.rowCount > 0 ? Math.round(f.ageSum / f.rowCount) : 0;

      var tr = document.createElement("tr");
      var oorClass = f.outOfRange > 0 ? " out-of-range-highlight" : "";
      tr.innerHTML =
        "<td>" + escapeHtml(fn) + "</td>" +
        '<td class="center">' + patientCount + "</td>" +
        '<td class="center">' + eventCount + "</td>" +
        '<td class="center">' + avgAge + "</td>" +
        '<td class="center">' + inpatientCount + "</td>" +
        '<td class="center' + oorClass + '">' + f.outOfRange + "</td>";
      tbody.appendChild(tr);
    });

    var section = document.querySelector("[data-summary]");
    if (section) section.hidden = false;
  }

  /* ------------------------------------------------------------------ */
  /*  Clinical Detail table (three-level grouped)                        */
  /* ------------------------------------------------------------------ */

  function buildClinicalDetail(rows, riskScores) {
    var tbody = document.querySelector("[data-rows]");
    if (!tbody) return;

    var currentFacility = null;
    var currentPatientId = null;
    var rowNum = 0;

    rows.forEach(function (r) {
      /* --- Facility banner --- */
      if (r.facilityName !== currentFacility) {
        currentFacility = r.facilityName;
        currentPatientId = null;

        var ftr = document.createElement("tr");
        ftr.className = "facility-banner";
        ftr.innerHTML = '<td colspan="9">Facility: ' +
          escapeHtml(r.facilityName) + " - " +
          escapeHtml(r.facilityCity) + ", " +
          escapeHtml(r.facilityState) + "</td>";
        tbody.appendChild(ftr);
      }

      /* --- Patient banner --- */
      if (r.patientId !== currentPatientId) {
        currentPatientId = r.patientId;

        var age = calculateAge(r.dateOfBirth);
        var bmi = calculateBmi(r.weightKg, r.heightCm);
        var bmiCat = getBmiCategory(bmi);
        var risk = riskScores[r.patientId] || 0;
        var isHighRisk = risk >= 4;

        var ptr = document.createElement("tr");
        ptr.className = "patient-banner " + (isHighRisk ? "high-risk" : "low-risk");
        ptr.innerHTML = '<td colspan="9">' +
          "Patient: <strong>" + escapeHtml(r.patientName) + "</strong>" +
          " &nbsp; MRN: " + escapeHtml(r.mrn) +
          " &nbsp; Age: " + age +
          " &nbsp; Sex: " + escapeHtml(r.gender) +
          " &nbsp; BMI: " + bmi + " (" + escapeHtml(bmiCat) + ")" +
          " &nbsp; Risk: " + risk +
          " &nbsp; Primary Dx: " + escapeHtml(r.primaryDiagnosis) +
          " &nbsp; Active meds: " + r.activeMedCount +
          "</td>";
        tbody.appendChild(ptr);
      }

      /* --- Detail row --- */
      rowNum++;
      var flag = getLabFlag(r.labValue, r.refLow, r.refHigh);
      var setting = r.isInpatient ? "Inpatient" : "Outpatient";
      var testName = r.labTestName != null ? escapeHtml(r.labTestName) : "-";
      var labResult = r.labValue != null
        ? escapeHtml(String(r.labValue) + " " + (r.labUnit || ""))
        : "-";
      var reference = r.refLow != null
        ? escapeHtml(String(r.refLow) + " - " + String(r.refHigh))
        : "-";
      var provider = escapeHtml(r.providerName) + " (" + escapeHtml(r.specialty) + ")";

      var flagTdClass = "flag-cell";
      if (flag === "OUT") flagTdClass += " flag-out";
      else if (flag === "OK") flagTdClass += " flag-ok";

      var settingTdClass = r.isInpatient ? " inpatient-cell" : "";

      var dtr = document.createElement("tr");
      dtr.className = rowNum % 2 === 1 ? "odd-row" : "even-row";
      dtr.innerHTML =
        "<td>" + escapeHtml(r.eventId) + "</td>" +
        "<td>" + formatDate(r.dateOfVisit) + "</td>" +
        "<td>" + provider + "</td>" +
        "<td>" + escapeHtml(r.donorType) + "</td>" +
        '<td class="' + settingTdClass.trim() + '">' + setting + "</td>" +
        "<td>" + testName + "</td>" +
        "<td>" + labResult + "</td>" +
        "<td>" + reference + "</td>" +
        '<td class="' + flagTdClass + '">' + flag + "</td>";
      tbody.appendChild(dtr);
    });

    var section = document.querySelector("[data-detail]");
    if (section) section.hidden = false;
  }

  /* ------------------------------------------------------------------ */
  /*  Filter echo (read-only applied-filters line)                       */
  /* ------------------------------------------------------------------ */

  function renderFiltersEcho(params) {
    var el = document.querySelector("[data-filters]");
    if (!el) return;
    var from = params.fromDate ? formatDate(params.fromDate) : "-";
    var to = params.toDate ? formatDate(params.toDate) : "-";
    var minAge = params.minAge != null ? params.minAge : "0";
    var maxAge = params.maxAge != null ? params.maxAge : "120";
    el.textContent = "Filters - Visit dates: " + from + " to " + to +
      " | Age: " + minAge + " to " + maxAge +
      " | Patient status: All";
  }

  /* ------------------------------------------------------------------ */
  /*  Narrative                                                          */
  /* ------------------------------------------------------------------ */

  function renderNarrative(narrative) {
    var el = document.querySelector("[data-narrative]");
    if (!el) return;
    if (narrative) {
      var sentences = narrative.split(/(?<=\.)\s+/);
      var paragraphs = [];
      for (var i = 0; i < sentences.length; i += 2) {
        var chunk = sentences.slice(i, i + 2).join(" ");
        paragraphs.push("<p>" + escapeHtml(chunk) + "</p>");
      }
      el.innerHTML =
        '<div class="report__narrative-header">' +
          '<svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor"><path d="M8 1a7 7 0 1 0 0 14A7 7 0 0 0 8 1zm0 1.5a1 1 0 1 1 0 2 1 1 0 0 1 0-2zM6.5 6.5h2v5h1v1h-3v-1h1v-4h-1v-1z"/></svg>' +
          'AI Summary' +
        '</div>' +
        '<div class="report__narrative-body">' + paragraphs.join("") + '</div>';
      el.hidden = false;
    } else {
      el.hidden = true;
    }
  }

  /* ------------------------------------------------------------------ */
  /*  Footer                                                             */
  /* ------------------------------------------------------------------ */

  function renderFooter(meta) {
    var genEl = document.querySelector("[data-generated]");
    var execEl = document.querySelector("[data-executed-by]");

    if (genEl && meta.generatedAt) {
      genEl.textContent = "Generated: " + formatDateTime(meta.generatedAt);
    }
    if (execEl && meta.executedBy) {
      execEl.textContent = " | Run by: " + meta.executedBy;
    }
  }

  /* ------------------------------------------------------------------ */
  /*  Main                                                               */
  /* ------------------------------------------------------------------ */

  document.addEventListener("DOMContentLoaded", function () {
    var data = getData();
    var rows = Array.isArray(data.rows) ? data.rows : [];
    var params = data.parameters || {};
    var meta = data.meta || {};

    wireFilterForm(params);
    renderFiltersEcho(params);
    renderFooter(meta);

    if (rows.length === 0) {
      var emptyEl = document.querySelector("[data-empty]");
      if (emptyEl) emptyEl.hidden = false;
      return;
    }

    sortRows(rows);

    var riskScores = computeRiskScores(rows);

    buildFacilitySummary(rows);
    buildClinicalDetail(rows, riskScores);
    renderNarrative(data.narrative);
  });
})();
