import { DISEASES } from "@/lib/diseaseInfo";

const escape = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

// Words that suggest a text is about vaccines. Deliberately broad: it only decides whether to warn that
// the results may not mean much, so a missed warning costs less than a wrong one.
const VACCINE_TERMS = [
  "vaccin\\w*", "vax\\w*", "anti-?vax\\w*", "jab\\w*", "booster\\w*", "shots?", "doses?", "inject\\w*", "needles?",
  "mrna", "immun\\w*", "inocul\\w*",
  "pfizer", "moderna", "astrazeneca", "novavax", "covid\\w*", "coronavirus", "sars-cov-2", "pandemic", "plandemic",
  "mmr", "flu", "influenza", "whooping cough", "pertussis", "tetanus", "rubella", "mumps", "rotavirus", "shingles", "autism",
  ...DISEASES.map((d) => escape(d.short.toLowerCase())),
];
const VACCINE_PATTERN = new RegExp(`\\b(?:${VACCINE_TERMS.join("|")})\\b`, "i");

export function looksVaccineRelated(text: string): boolean {
  return VACCINE_PATTERN.test(text);
}
