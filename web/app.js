"use strict";

var DAYS_PER_MONTH = 365.25 / 12;
var refs2006 = new Map();
var refs2007 = new Map();

var form = document.getElementById("calculator-form");
var analyzeButton = document.getElementById("analyze-button");
var resetButton = document.getElementById("reset-button");
var statusNode = document.getElementById("data-status");
var errorNode = document.getElementById("form-error");
var themeButton = document.getElementById("theme-toggle");

function parseTable(text, includeMode) {
  var lines = text.trim().split(/\r?\n/);
  var header = lines.shift().split("\t");
  var index = {};
  header.forEach(function (name, position) {
    index[name.toLowerCase()] = position;
  });
  var map = new Map();
  lines.forEach(function (line) {
    if (!line.trim()) return;
    var values = line.split("\t");
    var sex = Number(values[index.sex]);
    var age = Number(values[index.age]);
    map.set(sex + ":" + age, {
      L: Number(values[index.l]),
      M: Number(values[index.m]),
      S: Number(values[index.s]),
      mode: includeMode && index.loh !== undefined ? values[index.loh] : null
    });
  });
  return map;
}

function loadReferenceData() {
  return Promise.all([
    fetch("data/who_bmi_0_5.tsv").then(function (response) {
      if (!response.ok) throw new Error("Could not load WHO 2006 reference data.");
      return response.text();
    }),
    fetch("data/who_bmi_5_19.tsv").then(function (response) {
      if (!response.ok) throw new Error("Could not load WHO 2007 reference data.");
      return response.text();
    })
  ]).then(function (tables) {
    refs2006 = parseTable(tables[0], true);
    refs2007 = parseTable(tables[1], false);
    if (!refs2006.size || !refs2007.size) {
      throw new Error("WHO reference data are empty.");
    }
    statusNode.textContent = "Reference data ready";
    analyzeButton.disabled = false;
  }).catch(function (error) {
    statusNode.textContent = "Reference data unavailable";
    showError(error.message);
  });
}

function sexCode(value) {
  return value === "F" ? 2 : 1;
}

function referenceForAge(ageMonths, sex, ageDays) {
  var code = sexCode(sex);
  if (ageMonths < 60) {
    var day = Number.isFinite(ageDays) ? Math.round(ageDays) : Math.round(ageMonths * DAYS_PER_MONTH);
    var underFive = refs2006.get(code + ":" + day);
    if (!underFive) {
      throw new Error("Age is outside the WHO 2006 BMI-for-age reference.");
    }
    return {
      L: underFive.L,
      M: underFive.M,
      S: underFive.S,
      mode: underFive.mode,
      standard: "WHO Child Growth Standards 2006",
      displayAge: day + " days"
    };
  }

  if (ageMonths >= 229) {
    throw new Error("WHO BMI-for-age reference is available only below 229 months.");
  }

  var low = Math.floor(ageMonths);
  var high = Math.ceil(ageMonths);
  var lowRef = refs2007.get(code + ":" + low);
  var highRef = refs2007.get(code + ":" + high);
  if (!lowRef || !highRef) {
    throw new Error("Age is outside the WHO 2007 BMI-for-age reference.");
  }

  if (low === high) {
    return {
      L: lowRef.L,
      M: lowRef.M,
      S: lowRef.S,
      standard: "WHO Growth Reference 2007",
      displayAge: ageMonths.toFixed(2).replace(/\.00$/, "") + " months"
    };
  }

  var fraction = ageMonths - low;
  return {
    L: lowRef.L + fraction * (highRef.L - lowRef.L),
    M: lowRef.M + fraction * (highRef.M - lowRef.M),
    S: lowRef.S + fraction * (highRef.S - lowRef.S),
    standard: "WHO Growth Reference 2007",
    displayAge: ageMonths.toFixed(2) + " months"
  };
}

function rawZ(value, ref) {
  if (Math.abs(ref.L) < 1e-12) {
    return Math.log(value / ref.M) / ref.S;
  }
  return (Math.pow(value / ref.M, ref.L) - 1) / (ref.L * ref.S);
}

function measureAtZ(z, ref) {
  if (Math.abs(ref.L) < 1e-12) {
    return ref.M * Math.exp(ref.S * z);
  }
  var base = 1 + ref.L * ref.S * z;
  if (base <= 0) throw new Error("Reference parameters produced an invalid transformation.");
  return ref.M * Math.pow(base, 1 / ref.L);
}

function adjustedZ(value, ref) {
  var z = rawZ(value, ref);
  if (z > 3) {
    var p3 = measureAtZ(3, ref);
    var p2 = measureAtZ(2, ref);
    return 3 + (value - p3) / (p3 - p2);
  }
  if (z < -3) {
    var n3 = measureAtZ(-3, ref);
    var n2 = measureAtZ(-2, ref);
    return -3 + (value - n3) / (n2 - n3);
  }
  return z;
}

function erf(x) {
  var sign = x < 0 ? -1 : 1;
  var value = Math.abs(x);
  var t = 1 / (1 + 0.3275911 * value);
  var y = 1 - (((((1.061405429 * t - 1.453152027) * t) + 1.421413741) * t - 0.284496736) * t + 0.254829592) * t * Math.exp(-value * value);
  return sign * y;
}

function percentile(z) {
  return 50 * (1 + erf(z / Math.sqrt(2)));
}

function classify(z, ageMonths) {
  if (z < -3) return ageMonths < 60 ? "Very low BMI-for-age" : "Severe thinness";
  if (z < -2) return ageMonths < 60 ? "Low BMI-for-age" : "Thinness";
  if (ageMonths < 60) {
    if (z > 3) return "Obesity";
    if (z > 2) return "Overweight";
    if (z > 1) return "Risk of overweight";
    return "Normal";
  }
  if (z > 2) return "Obesity";
  if (z > 1) return "Overweight";
  return "Normal";
}

function categoryTone(category) {
  if (category === "Normal") return "normal";
  if (category === "Risk of overweight" || category === "Overweight" || category === "Thinness" || category === "Low BMI-for-age") return "review";
  if (category === "Ready") return "neutral";
  return "alert";
}

function numberFrom(id, required) {
  var raw = document.getElementById(id).value.trim();
  if (!raw && !required) return NaN;
  var value = Number(raw);
  if (!Number.isFinite(value)) throw new Error("Please enter valid numeric values.");
  return value;
}

function showError(message) {
  errorNode.textContent = message;
  errorNode.hidden = false;
}

function clearError() {
  errorNode.textContent = "";
  errorNode.hidden = true;
}

function setText(id, text) {
  document.getElementById(id).textContent = text;
}

function renderResult(result) {
  setText("bmi-result", result.bmi.toFixed(2));
  setText("z-result", (result.z >= 0 ? "+" : "") + result.z.toFixed(2));
  setText("percentile-result", result.percentile.toFixed(1) + "%");
  setText("category-result", result.category);
  setText("reference-age", result.ref.displayAge);
  setText("lms-result", result.ref.L.toFixed(4) + " / " + result.ref.M.toFixed(4) + " / " + result.ref.S.toFixed(5));
  setText("standard-result", result.ref.standard);
  setText("result-reference", result.ref.standard);

  var chip = document.getElementById("category-chip");
  chip.textContent = result.category;
  chip.className = "category-chip " + categoryTone(result.category);
}

function resetResult() {
  ["bmi-result", "z-result", "percentile-result", "category-result", "reference-age", "lms-result", "standard-result"].forEach(function (id) {
    setText(id, "—");
  });
  setText("result-reference", "Enter measurements and select Analyze.");
  var chip = document.getElementById("category-chip");
  chip.textContent = "Ready";
  chip.className = "category-chip neutral";
}

function analyze(event) {
  event.preventDefault();
  clearError();

  try {
    var ageMonths = numberFrom("age-months", true);
    var weight = numberFrom("weight", true);
    var height = numberFrom("height", true);
    var ageDays = numberFrom("age-days", false);
    var sex = document.getElementById("sex").value;

    if (ageMonths < 0 || ageMonths >= 229) throw new Error("Age must be from 0 to less than 229 months.");
    if (weight <= 0) throw new Error("Weight must be greater than zero.");
    if (height <= 0) throw new Error("Height or length must be greater than zero.");
    if (Number.isFinite(ageDays) && (ageDays < 0 || ageDays > 1826)) throw new Error("Exact age in days must be between 0 and 1826.");
    if (ageMonths >= 60 && Number.isFinite(ageDays)) throw new Error("Exact age in days is only used for children under 60 months.");
    if (Number.isFinite(ageDays) && Math.abs(ageMonths - ageDays / DAYS_PER_MONTH) > 0.55) {
      throw new Error("Age in months and exact age in days do not agree. Correct one of the age fields.");
    }

    var effectiveAgeMonths = Number.isFinite(ageDays) ? ageDays / DAYS_PER_MONTH : ageMonths;
    var bmi = weight / Math.pow(height / 100, 2);
    var ref = referenceForAge(effectiveAgeMonths, sex, ageDays);
    var z = adjustedZ(bmi, ref);
    var result = {
      bmi: bmi,
      z: z,
      percentile: percentile(z),
      category: classify(z, effectiveAgeMonths),
      ref: ref
    };
    renderResult(result);
  } catch (error) {
    showError(error instanceof Error ? error.message : "Unable to calculate result.");
  }
}

function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
  themeButton.textContent = theme === "dark" ? "Light" : "Dark";
  themeButton.setAttribute("aria-label", "Switch to " + (theme === "dark" ? "light" : "dark") + " theme");
}

function initialTheme() {
  var saved = localStorage.getItem("bmi-theme");
  if (saved === "dark" || saved === "light") return saved;
  return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

themeButton.addEventListener("click", function () {
  var next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
  localStorage.setItem("bmi-theme", next);
  applyTheme(next);
});

form.addEventListener("submit", analyze);

resetButton.addEventListener("click", function () {
  form.reset();
  clearError();
  resetResult();
});

applyTheme(initialTheme());
loadReferenceData();
