// Content from the "Vaccine-Preventable Diseases Fact Compendium", compiled 1 October 2026 from WHO, CDC and the
// Australian Department of Health, Disability and Ageing. Text wrapped in **double asterisks** renders bold.

export const COMPILED_ON = "1 October 2026";

export type Region = "au" | "us" | "who";

export const REGION_LABEL: Record<Region, string> = {
  au: "Australia",
  us: "United States",
  who: "WHO",
};

export const REGION_SOURCE: Record<Region, string> = {
  au: "Department of Health, Disability and Ageing (NIP Schedule, June 2026) and the Australian Immunisation Handbook",
  us: "CDC web pages. US recommendations are currently in legal flux",
  who: "WHO fact sheets and position papers",
};

export type Section = { heading: string; paras?: string[]; bullets?: string[] };
export type Source = { label: string; url: string };

export type Disease = {
  id: string;
  name: string;
  short: string;
  headline: string;
  facts: [string, string][];
  sections: Section[];
  vaccination: Record<Region, string[]>;
  sources: Source[];
};

const NIP_SCHEDULE: Source = {
  label: "Dept of Health NIP Schedule (June 2026)",
  url: "https://www.health.gov.au/sites/default/files/2026-06/national-immunisation-program-schedule.pdf",
};

export const READ_FIRST: string[] = [
  "**Sources and dates.** Each section was drawn from the live WHO, CDC and Australian Department of Health pages as at 1 October 2026. Page dates are given where the source shows one.",
  "**Department name.** The Australian department is now called the Department of Health, Disability and Ageing (previously Health and Aged Care). Its National Immunisation Program (NIP) Schedule used here is the version current from June 2026.",
  "**COVID-19 funding changed on 1 October 2026.** COVID-19 vaccines moved from the stand-alone National COVID-19 Vaccine Program onto the NIP, with free vaccine limited to higher-risk groups.",
  "**US recommendations are in legal flux.** In January 2026 US federal officials revised the CDC childhood schedule without the usual ACIP process. A federal court stayed that revision on 16 March 2026, and CDC pages for most diseases describe the longer-standing recommendations.",
];

export const DISEASES: Disease[] = [
  {
    id: "covid-19",
    name: "COVID-19",
    short: "COVID-19",
    headline: "About 780 million cases and 7.1 million deaths reported since Dec 2019 (WHO)",
    facts: [
      ["Cause", "SARS-CoV-2 coronavirus"],
      ["Spread", "Infectious respiratory particles in the air; also touching contaminated surfaces then the eyes, nose or mouth"],
      ["Incubation", "Usually 3 to 6 days after exposure; symptoms last up to about 10 days, sometimes longer"],
      ["Vaccine", "mRNA and protein-based vaccines updated for circulating variants"],
      ["Australia, from 1 Oct 2026", "NIP-funded for people at highest risk of severe disease"],
    ],
    sections: [
      {
        heading: "Overview",
        paras: [
          "COVID-19 is caused by the SARS-CoV-2 virus. WHO reports nearly 780 million cases and more than 7.1 million deaths worldwide since December 2019, noting the true figures are thought to be higher. WHO ended the Public Health Emergency of International Concern in May 2023, but describes COVID-19 as a continuing significant public health concern, with the virus circulating all year and no established seasonal pattern.",
        ],
      },
      {
        heading: "How it spreads",
        paras: [
          "The virus spreads through the air when an infected person breathes, talks, coughs or sneezes. Spread is more likely in close contact or shared indoor spaces. People can pass on the virus without symptoms or in the days before symptoms begin.",
        ],
      },
      {
        heading: "Symptoms and complications",
        bullets: [
          "**Most common symptoms (currently circulating variants):** fever, chills and sore throat.",
          "**Less common:** muscle aches, severe fatigue, runny or blocked nose, headache, sore eyes, dizziness, new persistent cough, tight chest, shortness of breath, hoarse voice, numbness or tingling, appetite loss, nausea, vomiting, abdominal pain, diarrhoea, change in taste or smell, difficulty sleeping.",
          "**Seek immediate care for:** difficulty breathing at rest or inability to speak in sentences, confusion, drowsiness or loss of consciousness, persistent chest pain or pressure, cold clammy or pale or bluish skin, loss of speech or movement.",
          "**Severe disease** can involve respiratory failure, sepsis, blood clots and multi-organ failure. In rare cases children develop a severe inflammatory syndrome a few weeks after infection.",
          "**Post COVID-19 condition (long COVID):** about 6% of people develop it. Common symptoms are fatigue, muscle or joint pain, breathlessness, headaches and difficulty concentrating.",
        ],
      },
      {
        heading: "Who is at higher risk",
        paras: [
          "Older adults, people with underlying conditions (high blood pressure, diabetes, obesity, chronic lung, heart, liver or kidney disease, cancer, dementia, rheumatological conditions), people who are immunosuppressed (including those taking immunosuppressive medicines or living with HIV), pregnant women, and unvaccinated people. Health and care workers have higher exposure.",
        ],
      },
      {
        heading: "Treatment",
        paras: [
          "Most people recover from mild illness without treatment. Medical treatments exist for people who are at risk of severe illness; health professionals choose them based on severity, age, symptoms and other health conditions.",
        ],
      },
      {
        heading: "Prevention",
        bullets: [
          "Stay home and away from others if you have symptoms or test positive.",
          "Wear a properly fitted mask around others if you have symptoms; carers of high-risk people should wear a medical mask.",
          "Cover coughs and sneezes with a bent elbow or tissue; clean hands often with soap and water or alcohol-based rub.",
          "Improve indoor ventilation by opening windows and doors.",
          "Avoid close contact with people who have respiratory symptoms, and avoid crowded or poorly ventilated places if you are at high risk.",
        ],
      },
    ],
    vaccination: {
      au: [
        "From **1 October 2026**, COVID-19 vaccines are funded under the NIP, replacing the National COVID-19 Vaccine Program set up during the pandemic. Funded access is no longer universal.",
        "**Free eligibility:** all adults 75 and over (two doses a year, about six months apart); adults 65 to 74 (one dose a year); Aboriginal and Torres Strait Islander people 50 to 74 (one dose a year); adults 18 to 64 with severe immunocompromise (one dose a year).",
        "People outside these groups can buy the vaccine privately after discussing it with their health provider.",
        "NIP funding generally requires a Medicare card or eligibility. Updated ATAGI recommendations are published in the Australian Immunisation Handbook from 1 October 2026; check it for current product and dosing details.",
      ],
      us: [
        "A 2026 to 2027 COVID-19 vaccine is recommended for all adults aged 18 and over.",
        "Children 6 months to 17 years with moderate to severe immunocompromise: recommended. All other children in that age range: shared clinical decision-making between parents and clinicians.",
        "CDC states that, because of legal uncertainties, the recommendations from the July 2025 immunization schedule remain in effect for the 2026 to 2027 season.",
      ],
      who: [
        "WHO recommends a risk-based approach. A single dose can be considered for people who have not yet been vaccinated.",
        "Revaccination 6 to 12 months after the last dose may be needed for high-priority groups: older adults, people with severe obesity or multiple significant comorbidities, people with immunocompromising conditions, pregnant women and health workers with direct patient contact.",
        "Vaccines protect strongly against severe illness, hospitalisation and death but have limited impact on reducing transmission.",
      ],
    },
    sources: [
      { label: "WHO COVID-19 fact sheet (27 Nov 2025)", url: "https://www.who.int/news-room/fact-sheets/detail/coronavirus-disease-(covid-19)" },
      { label: "Dept of Health: COVID-19 vaccine moving to the NIP", url: "https://www.health.gov.au/topics/immunisation/vaccines/covid-19-vaccine" },
      { label: "CDC COVID-19 vaccine overview", url: "https://www.cdc.gov/covid/hcp/vaccine-considerations/overview.html" },
    ],
  },
  {
    id: "meningitis",
    name: "Meningitis",
    short: "Meningitis",
    headline: "About 1 in 6 people with bacterial meningitis die; 1 in 5 survivors have long-term effects (WHO)",
    facts: [
      ["Cause", "Bacteria, viruses, fungi or parasites. Bacterial meningitis is the greatest concern: meningococcus, pneumococcus, Haemophilus influenzae type b (Hib) and group B streptococcus (GBS)"],
      ["Spread", "Respiratory particles and throat secretions; GBS passes from mother to baby during birth"],
      ["Severity", "About 1 in 6 people with bacterial meningitis die and 1 in 5 have severe complications (WHO)"],
      ["Vaccines", "Meningococcal (MenACWY, MenB), pneumococcal conjugate, Hib. No universal vaccine exists"],
      ["Medical emergency", "Needs urgent treatment in hospital"],
    ],
    sections: [
      {
        heading: "Overview",
        paras: [
          "Meningitis is inflammation of the membranes around the brain and spinal cord. It can affect anyone at any age, and the organisms involved vary with age, immune status and living conditions. WHO describes it as a devastating disease that can be deadly and often causes serious long-term health problems.",
        ],
        bullets: [
          "**Newborns:** most at risk from group B streptococcus.",
          "**Children and adolescents:** most at risk from meningococcus, pneumococcus and Haemophilus influenzae.",
          "**Adults:** pneumococcus and meningococcus cause most bacterial meningitis.",
          "**Immunocompromised people and people living with HIV** are at increased risk of different types of meningitis.",
        ],
      },
      {
        heading: "How it spreads",
        paras: [
          "Meningococcus, pneumococcus and Haemophilus influenzae are carried in the nose and throat and spread person to person by respiratory particles or throat secretions. Carrying these bacteria is usually harmless and builds immunity; only occasionally do they invade the body and cause meningitis or sepsis. Meningococcal outbreaks are more frequent in crowded settings such as mass gatherings, refugee settings, closed institutions and military camps.",
        ],
      },
      {
        heading: "Symptoms",
        bullets: [
          "**Common:** fever, neck stiffness, confusion or altered mental state, headache, sensitivity to light, nausea and vomiting.",
          "**Less frequent:** seizures, coma, weakness of the limbs.",
          "**Infants:** unusually inactive or hard to wake, irritability, weak continuous cry, poor feeding, bulging soft spot on the head.",
          "**Sepsis signs:** cold hands and feet, fast breathing, low blood pressure. A non-blanching skin rash can appear with meningococcal sepsis.",
        ],
      },
      {
        heading: "Complications",
        paras: [
          "One in five survivors of bacterial meningitis may have lasting effects: hearing loss, seizures, limb weakness, and difficulties with vision, speech, language, memory and communication, as well as scarring and limb amputations after sepsis.",
        ],
      },
      {
        heading: "Global burden",
        paras: [
          "The African meningitis belt, from Senegal to Ethiopia, carries the highest burden. In 2025, 24 of the 26 countries in the belt's enhanced surveillance network reported 21,526 suspected cases and 971 deaths to WHO (case fatality rate 4.5%).",
        ],
      },
      {
        heading: "Diagnosis and treatment",
        paras: [
          "Diagnosis needs a lumbar puncture to examine cerebrospinal fluid, but WHO stresses it should never delay antibiotics if bacterial meningitis is suspected. Treatment is urgent: antibiotics as soon as possible, with a corticosteroid such as dexamethasone started with the first dose in non-epidemic settings to reduce inflammation and the risk of neurological harm and death.",
        ],
      },
      {
        heading: "Prevention",
        bullets: [
          "Vaccines give the best protection against meningococcus, pneumococcus and Hib.",
          "Close contacts of someone with meningococcal disease are offered antibiotics to clear the bacteria from the nose and throat.",
          "Household contacts should wash hands often, avoid close contact and avoid sharing cups, utensils or toothbrushes.",
          "In many countries, women at risk of passing GBS to their babies are offered intravenous penicillin during labour.",
          "WHO notes no confirmed serogroup A meningitis case has been reported since 2017 in meningitis-belt countries that introduced the MenA conjugate vaccine. A five-serogroup conjugate vaccine (Men5CV) was prequalified in 2023.",
        ],
      },
    ],
    vaccination: {
      au: [
        "**MenACWY:** Nimenrix at 12 months; MenQuadfi in Year 10 (14 to 16 years).",
        "**MenB (Bexsero):** NIP-funded at 2, 4 and 12 months for Aboriginal and Torres Strait Islander children, and at 6 months for children with specified medical risk conditions. Prophylactic paracetamol is recommended. It is recommended but not NIP-funded for other children.",
        "**Pneumococcal (Prevenar 20):** 2, 4 and 12 months; an extra dose at 6 months for Aboriginal and Torres Strait Islander children and children with specified risk conditions.",
        "**Hib:** in the hexavalent vaccine at 2, 4 and 6 months and ActHIB at 18 months.",
        "People with specified medical risk conditions (for example asplenia) can receive additional MenACWY and MenB doses; see the Immunisation Handbook.",
      ],
      us: [
        "**Long-standing schedule:** MenACWY routinely at 11 to 12 years with a booster at 16; MenB by shared clinical decision-making at 16 to 23 years.",
        "Hib and pneumococcal conjugate vaccines are given in infancy.",
        "The January 2026 revised schedule would have changed the recommendation type for meningococcal vaccines; it is stayed.",
      ],
      who: [
        "Hib vaccine is used in most national childhood programmes and WHO recommends universal pneumococcal conjugate vaccine (PCV).",
        "Meningococcal vaccines include multivalent conjugate vaccines (A, C, W, Y, X) and protein-based MenB vaccines.",
      ],
    },
    sources: [
      { label: "WHO meningitis fact sheet (29 Sep 2026)", url: "https://www.who.int/news-room/fact-sheets/detail/meningitis" },
      NIP_SCHEDULE,
    ],
  },
  {
    id: "hpv",
    name: "Human papillomavirus (HPV)",
    short: "HPV",
    headline: "Types 16 and 18 cause about 76% of cervical cancers (WHO)",
    facts: [
      ["Cause", "Human papillomavirus; high-risk types cause cancer"],
      ["Spread", "Common sexually transmitted infection; can affect the skin, genital area, anal area and throat"],
      ["Cancer link", "Persistent infection with high-risk types causes almost all cervical cancer. Types 16 and 18 cause about 76% of cervical cancers (WHO)"],
      ["Vaccine", "Gardasil 9 (nine-valent) used in Australia and the US"],
      ["Australia", "Single dose at 12 to 13 years (Year 7); free catch-up to 25"],
    ],
    sections: [
      {
        heading: "Overview",
        paras: [
          "Almost all sexually active people are infected with HPV at some point, usually without symptoms, and the immune system usually clears the virus. Persistent infection with certain carcinogenic types can cause abnormal cells that develop into cancer. For cervical cancer this typically takes 15 to 20 years, or 5 to 10 years in women with weakened immune systems such as untreated HIV.",
        ],
      },
      {
        heading: "Cervical cancer burden (WHO)",
        bullets: [
          "Fifth most commonly diagnosed cancer in women globally, with about 604,000 new cases and about 280,000 deaths in 2024.",
          "Highest rates are in low- and middle-income countries, reflecting unequal access to vaccination, screening and treatment.",
          "Women living with HIV are 6 times more likely to develop cervical cancer.",
          "Cervical cancer is largely preventable through HPV vaccination and regular screening, and can be cured if found early and treated promptly.",
        ],
      },
      {
        heading: "Symptoms to act on",
        paras: [
          "Precancers rarely cause symptoms, which is why screening matters even after vaccination. WHO advises seeing a health professional about unusual bleeding between periods, after menopause or after sex; increased or foul-smelling vaginal discharge; persistent back, leg or pelvic pain; weight loss, fatigue and appetite loss; vaginal discomfort; or leg swelling.",
        ],
      },
      {
        heading: "Screening and prevention (WHO)",
        bullets: [
          "HPV vaccination, ideally before sexual activity begins.",
          "Cervical screening with a high-performance test every 5 to 10 years from age 30 (every 3 to 5 years from age 25 for women living with HIV). Self-collected samples are as reliable as clinician-collected samples.",
          "Not smoking, using condoms and voluntary male circumcision also reduce risk.",
          "Global elimination targets by 2030 (\"90-70-90\"): 90% of girls fully vaccinated by age 15, 70% of women screened by 35 and again by 45, and 90% of women with precancer or cancer treated.",
        ],
      },
    ],
    vaccination: {
      au: [
        "**Gardasil 9, single dose** recommended at 12 to 13 years (Year 7 or age equivalent), usually in school.",
        "A missed dose is available free as catch-up up to and including 25 years of age.",
        "People aged 12 to 26 with specified medical risk conditions that increase HPV risk are recommended 3 doses (see Immunisation Handbook for eligibility and intervals).",
      ],
      us: [
        "Routine vaccination at 11 or 12 years (can start at 9). Catch-up through age 26. Shared clinical decision-making for some adults 27 to 45.",
        "**Two doses** (0 and 6 to 12 months) if started before the 15th birthday; **three doses** (0, 1 to 2, and 6 months) if started at 15 to 26 years and for immunocompromised people aged 9 to 26.",
        "The January 2026 revised childhood schedule would have reduced HPV to a single dose; that revision is stayed by a court order.",
      ],
      who: [
        "HPV vaccination is a priority for girls aged 9 to 14 years. Depending on the national schedule it may be given as one or two doses; people with compromised immune systems, including those living with HIV, should ideally receive two or three doses.",
        "In 2022 WHO's SAGE endorsed a single-dose option for girls 9 to 14 and young women 15 to 20, finding comparable protection to two-dose schedules.",
        "As of 2025 there were 8 licensed HPV vaccines, five WHO-prequalified. Some countries also vaccinate boys.",
      ],
    },
    sources: [
      { label: "WHO cervical cancer fact sheet (3 Jul 2026)", url: "https://www.who.int/news-room/fact-sheets/detail/cervical-cancer" },
      {
        label: "WHO single-dose HPV news (2022)",
        url: "https://www.who.int/news/item/11-04-2022-one-dose-human-papillomavirus-(hpv)-vaccine-offers-solid-protection-against-cervical-cancer",
      },
      { label: "CDC HPV vaccination considerations", url: "https://www.cdc.gov/hpv/hcp/vaccination-considerations/index.html" },
      NIP_SCHEDULE,
    ],
  },
  {
    id: "chickenpox",
    name: "Chickenpox (varicella)",
    short: "Chickenpox",
    headline: "Two doses about 90% effective (CDC)",
    facts: [
      ["Cause", "Varicella-zoster virus (VZV)"],
      ["Spread", "Highly contagious person to person"],
      ["Incubation", "Rash usually appears 10 to 21 days after exposure"],
      ["Vaccine", "Live attenuated varicella vaccine, alone or combined with MMR (MMRV)"],
      ["Effectiveness", "Two doses are about 90% effective at preventing chickenpox (CDC)"],
      ["Link to shingles", "The virus stays dormant in the body and can reactivate years later as shingles (herpes zoster)"],
    ],
    sections: [
      {
        heading: "Overview",
        paras: [
          "Chickenpox causes an itchy rash that usually lasts about a week, with fever, tiredness, loss of appetite and headache. In unvaccinated people the rash progresses quickly from flat spots to raised spots to fluid-filled blisters before crusting. A mild feverish illness may come 1 to 2 days before the rash, particularly in adults. WHO does not publish a stand-alone chickenpox fact sheet, so clinical detail here is mainly from CDC.",
        ],
      },
      {
        heading: "Complications",
        paras: [
          "The disease is usually mild but can be serious. The most common complications are bacterial skin and soft-tissue infections in children and pneumonia in adults. CDC also lists blood vessel inflammation, swelling of the brain or spinal cord coverings, and infections of the bloodstream, bone or joints. Severe disease is more likely in pregnancy, in infants under 12 months, in adolescents and adults, and in people with weakened immune systems. People can die from chickenpox, although this is uncommon.",
        ],
      },
      {
        heading: "Breakthrough chickenpox",
        paras: [
          "If a vaccinated person gets chickenpox it is usually mild, with fewer or no blisters and low or no fever. Breakthrough disease is less frequent after two doses than after one.",
        ],
      },
    ],
    vaccination: {
      au: [
        "Varicella is given as the combined **MMRV vaccine (Priorix-Tetra) at 18 months**.",
        "All people under 20 who missed childhood vaccines are eligible for NIP catch-up. Refugees and humanitarian entrants aged 20 and over are eligible for chickenpox catch-up if missed.",
        "Shingles vaccine (Shingrix, 2 doses) is separately NIP-funded for all adults 65 and over, Aboriginal and Torres Strait Islander adults 50 and over, and adults 18 and over with specified medical risk conditions.",
      ],
      us: [
        "**Two doses:** first at 12 to 15 months, second at 4 to 6 years. Separate MMR and varicella vaccines are recommended for the first dose at 12 to 47 months, although MMRV may be used if parents prefer.",
        "People 13 and older without evidence of immunity: 2 doses at least 28 days apart (4 to 8 weeks).",
        "After exposure, people without immunity should get the vaccine, ideally within 3 to 5 days.",
        "Pregnant women should not receive the vaccine.",
      ],
      who: [
        "WHO's 2014 position paper says countries where varicella is an important public health burden could introduce routine childhood vaccination (generally at 12 to 18 months).",
        "Two doses give higher effectiveness and are recommended where the goal is also to reduce cases and outbreaks.",
        "Countries should also consider two doses for non-immune health workers and for household contacts of immunocompromised people.",
      ],
    },
    sources: [
      { label: "CDC chickenpox vaccine considerations", url: "https://www.cdc.gov/chickenpox/hcp/vaccine-considerations/index.html" },
      { label: "CDC chickenpox vaccination", url: "https://www.cdc.gov/chickenpox/vaccines/index.html" },
      {
        label: "WHO varicella position paper summary (2014)",
        url: "https://cdn.who.int/media/docs/default-source/immunization/position_paper_documents/varicella/who-pp-varicella-herpes-zoster-june2014-summary.pdf?sfvrsn=21158d4d_2",
      },
      NIP_SCHEDULE,
    ],
  },
  {
    id: "hepatitis-a",
    name: "Hepatitis A",
    short: "Hep A",
    headline: "Never becomes chronic (WHO, CDC)",
    facts: [
      ["Cause", "Hepatitis A virus (HAV)"],
      ["Spread", "Faecal-oral: contaminated food or water, or close personal contact. Not spread by sneezing or coughing"],
      ["Incubation", "Average 28 days (range 15 to 50) per CDC; symptoms usually appear 2 to 7 weeks after exposure"],
      ["Chronic infection?", "No. Hepatitis A does not become chronic and, unlike hepatitis B and C, does not cause chronic liver disease"],
      ["Vaccine", "Inactivated vaccine; two doses give long-lasting protection"],
    ],
    sections: [
      {
        heading: "Overview",
        paras: [
          "Hepatitis A is a viral liver disease. Illness ranges from mild to severe. Almost everyone recovers fully and gains lifelong immunity, though a very small proportion of people die from fulminant hepatitis (acute liver failure). WHO describes it as one of the most frequent causes of foodborne infection. It cannot be told apart from other types of acute viral hepatitis on symptoms alone, so blood tests are needed.",
        ],
      },
      {
        heading: "Symptoms",
        bullets: [
          "Fever, tiredness, loss of appetite, stomach pain, nausea, vomiting, diarrhoea, joint pain.",
          "Jaundice (yellow skin and eyes), dark urine and pale stools.",
          "Adults are more likely than children to have symptoms; children can spread the virus without ever being ill.",
          "Symptoms usually last under 2 months, but 10% to 15% of symptomatic people have prolonged or relapsing illness for up to 6 months (CDC).",
          "People can pass the virus on for up to about 2 weeks before symptoms appear.",
        ],
      },
      {
        heading: "Who is at risk",
        bullets: [
          "Anyone not vaccinated or previously infected.",
          "Travellers to, and residents of, areas where hepatitis A is common.",
          "Household members and sexual partners of someone with hepatitis A.",
          "In the US, outbreaks have mainly spread person to person among people who use drugs, people experiencing homelessness, and men who have sex with men.",
          "People with chronic liver disease (including hepatitis B or C) face more serious illness, as do older people.",
        ],
      },
      {
        heading: "Treatment and prevention",
        bullets: [
          "There is no specific antiviral treatment; care focuses on rest, fluids and symptom relief.",
          "Vaccination is the best prevention.",
          "Good hand hygiene, safe food and water, and not working as a food handler while ill reduce spread. People with hepatitis A should avoid giving it to others, for example by washing hands carefully after toilet use and avoiding preparing food for others.",
        ],
      },
      {
        heading: "Occurrence",
        paras: [
          "In 2023, 1,648 cases were reported in the US, with CDC estimating about 3,300 actual infections. People aged 30 to 39 had the highest rate that year.",
        ],
      },
    ],
    vaccination: {
      au: [
        "**Vaqta Paediatric at 18 months and 4 years** is NIP-funded for Aboriginal and Torres Strait Islander children in WA, NT, SA and Queensland (two doses at least 6 months apart; the 4-year dose is not needed if two doses were already given from age 12 months).",
        "The Immunisation Handbook recommends vaccination for other people at increased risk, such as travellers to countries where hepatitis A is common. NSW Health also lists these as at-risk groups.",
      ],
      us: [
        "A 2-dose series. Routine for children at 12 to 23 months, and for adults at risk.",
        "A combined hepatitis A and B vaccine (Twinrix) has been available since 2001.",
        "The January 2026 revised schedule would have changed hepatitis A to a shared-decision or risk-based recommendation for children; it is stayed.",
      ],
      who: ["Several injectable inactivated vaccines are available internationally, and some countries use a single-dose schedule."],
    },
    sources: [
      { label: "WHO hepatitis A fact sheet", url: "https://who.int/news-room/fact-sheets/detail/hepatitis-a" },
      { label: "CDC hepatitis A basics", url: "https://www.cdc.gov/hepatitis-a/about/index.html" },
      { label: "CDC hepatitis A clinical overview", url: "https://www.cdc.gov/hepatitis-a/hcp/clinical-overview/index.html" },
      { label: "NSW Health hepatitis A fact sheet", url: "https://www.health.nsw.gov.au/Infectious/factsheets/Pages/hepatitis_a.aspx" },
      NIP_SCHEDULE,
    ],
  },
  {
    id: "hepatitis-b",
    name: "Hepatitis B",
    short: "Hep B",
    headline: "240 million chronic infections; 1.1 million deaths in 2024 (WHO)",
    facts: [
      ["Cause", "Hepatitis B virus (HBV), which attacks the liver"],
      ["Spread", "Infected blood and body fluids; mother to child; unsafe injections; sexual contact"],
      ["Chronic risk", "Infection in infancy or early childhood becomes chronic in about 95% of cases; in adulthood, less than 5%"],
      ["Global burden (2024)", "240 million people with chronic infection; 0.9 million new infections; 1.1 million deaths (WHO)"],
      ["Vaccine", "Safe and effective; protects for at least 20 years and probably for life"],
    ],
    sections: [
      {
        heading: "Overview",
        paras: [
          "Hepatitis B can cause acute (short and severe) or chronic (long-term) infection and puts people at high risk of death from cirrhosis and liver cancer. WHO estimates that in 2024 about 65 million people, or 27% of those living with hepatitis B, knew their infection status. Hepatitis B cannot be diagnosed on symptoms alone; blood tests are essential.",
        ],
      },
      {
        heading: "Transmission",
        paras: [
          "The virus is transmitted through contact with infected blood and body fluids, from mother to child, through unsafe injection practices and through sexual contact. In high-prevalence regions it is most commonly spread from mother to child at birth or between young children. The virus can survive outside the body for at least 7 days. The incubation period averages about 75 days (range 30 to 180).",
        ],
      },
      {
        heading: "Symptoms",
        paras: [
          "Many people, especially children, have no symptoms during acute infection. When symptoms occur they can include jaundice, tiredness, dark urine, nausea and abdominal pain. A small subset of people with acute hepatitis develop acute liver failure, which can be fatal. Chronic infection can progress silently to cirrhosis or liver cancer.",
        ],
      },
      {
        heading: "Treatment",
        bullets: [
          "No specific treatment exists for acute hepatitis B; care focuses on managing symptoms.",
          "Chronic hepatitis B is treated with oral antivirals such as tenofovir or entecavir. Most people who start treatment continue it for life.",
          "WHO's 2025 guideline recommends treating adults and adolescents aged 12 and over with chronic infection and significant fibrosis or cirrhosis, and testing all pregnant women for hepatitis B.",
        ],
      },
      {
        heading: "Prevention",
        bullets: [
          "All babies should receive the first hepatitis B vaccine dose as soon as possible after birth, within 24 hours, followed by two or three further doses at least four weeks apart.",
          "Health-care workers should be vaccinated.",
          "Safe injection practices, safer sex and testing of blood products reduce risk.",
        ],
      },
    ],
    vaccination: {
      au: [
        "**Birth dose** (Engerix B Paediatric), ideally within 24 hours and no later than 7 days after birth.",
        "**Hexavalent vaccine** (Infanrix hexa or Vaxelis) at 2, 4 and 6 months includes hepatitis B.",
        "People under 20 who missed doses are eligible for NIP catch-up. Refugees and humanitarian entrants of any age are eligible for catch-up hepatitis B vaccine. Other adults at risk should see the Immunisation Handbook.",
      ],
      us: [
        "CDC web pages recommend hepatitis B vaccine for all infants (including a birth dose regardless of the birth parent's status, with immune globulin for infants of infected parents), unvaccinated children under 19, all adults 19 to 59, and adults 60 and over with risk factors.",
        "In December 2025 ACIP voted to end the universal birth dose for infants of mothers who test negative, and CDC adopted it. That vote and others taken after 11 June 2025 were stayed by a federal court on 16 March 2026.",
      ],
      who: [
        "Birth dose within 24 hours for all infants, followed by two or three doses at least four weeks apart.",
        "WHO also recommends testing and vaccinating at-risk groups, including household and sexual contacts and health-care workers.",
      ],
    },
    sources: [
      { label: "WHO hepatitis B fact sheet", url: "https://www.who.int/news-room/fact-sheets/detail/hepatitis-b" },
      { label: "CDC hepatitis B vaccination", url: "https://www.cdc.gov/hepatitis-b/vaccination/index.html" },
      { label: "CDC perinatal vaccine information", url: "https://www.cdc.gov/hepatitis-b/hcp/perinatal-provider-overview/vaccine-administration.html" },
      NIP_SCHEDULE,
    ],
  },
  {
    id: "measles",
    name: "Measles (and MMR vaccine)",
    short: "Measles",
    headline: "One case can infect up to 18 others; about 95,000 deaths in 2024 (WHO)",
    facts: [
      ["Cause", "Measles virus"],
      ["Spread", "Airborne; infected nasal and throat secretions. The virus stays active in the air or on surfaces for up to 2 hours"],
      ["Contagiousness", "One infected person can generate up to 18 secondary infections; infectious from 4 days before the rash to 4 days after"],
      ["Incubation", "Symptoms begin 7 to 14 days after exposure"],
      ["Vaccine", "MMR (measles, mumps, rubella), or MMRV with varicella; two doses needed"],
      ["Deaths in 2024", "About 95,000, mostly unvaccinated or under-vaccinated children under 5 (WHO)"],
    ],
    sections: [
      {
        heading: "Overview",
        paras: [
          "Measles is a highly contagious, serious airborne disease. Before the vaccine was introduced in 1963, major epidemics occurred about every two to three years and caused an estimated 2.6 million deaths a year. WHO estimates vaccination averted nearly 59 million deaths between 2000 and 2024, cutting deaths from 780,000 to 95,000. Measles remains common in parts of Africa, the Middle East and Asia.",
        ],
      },
      {
        heading: "Symptoms",
        bullets: [
          "**Early (4 to 7 days):** fever, runny nose, cough, red and watery eyes, small white spots inside the cheeks.",
          "**Rash:** appears 3 to 5 days after the first symptoms, usually on the face and upper neck, spreading downward over about 3 days and lasting 4 to 8 days.",
        ],
      },
      {
        heading: "Complications",
        paras: [
          "Most deaths come from complications: blindness, encephalitis (brain swelling), severe diarrhoea and dehydration, ear infections and severe breathing problems including pneumonia. Complications are most common in children under 5 and adults over 30, and in malnourished children, especially those lacking vitamin A or with weak immune systems. Measles also weakens the immune system and can make the body \"forget\" how to defend against other infections. Measles in pregnancy can be dangerous and can cause miscarriage or premature birth.",
        ],
      },
      {
        heading: "Who is at risk",
        paras: [
          "Anyone who is not immune. Unvaccinated young children and pregnant people are at highest risk of severe complications. Outbreaks are more likely where routine immunisation is disrupted, such as conflict zones, disaster areas and crowded camps.",
        ],
      },
      {
        heading: "Treatment",
        paras: [
          "There is no specific treatment. Care focuses on relieving symptoms, fluids for dehydration and antibiotics for secondary infections such as pneumonia or ear infections. WHO recommends two doses of vitamin A, on diagnosis and the next day, for children under 5 with suspected measles.",
        ],
      },
      {
        heading: "Global coverage (WHO)",
        paras: [
          "In 2025 about 84% of children received a first dose by their first birthday and 77% received both doses. WHO says at least 95% coverage with two doses is needed to stop transmission; about 29 million infants were under-protected in 2025.",
        ],
      },
    ],
    vaccination: {
      au: [
        "**MMR (Priorix) at 12 months** and **MMRV (Priorix-Tetra) at 18 months** on the NIP.",
        "**Adolescents and adults born during or since 1966** should have documented evidence of 2 doses of measles-containing vaccine at least 4 weeks apart (both given at 12 months or older), or serological evidence of immunity. Those without evidence should be vaccinated. People born before 1966 generally do not need vaccine.",
        "MMR is the only measles-containing vaccine recommended for people 14 years and over. NIP funds catch-up for people under 20.",
        "Travellers born during or since 1966 should have had 2 doses. Infants aged 6 to under 12 months can receive a dose before overseas travel or during outbreaks but still need the routine doses at 12 and 18 months.",
        "After exposure, MMR given within 72 hours can help prevent illness in people without immunity.",
      ],
      us: [
        "Children: 2 doses of MMR, at 12 to 15 months and 4 to 6 years.",
        "Adults without evidence of immunity: at least 1 dose; 2 doses (at least 28 days apart) for health-care personnel, international travellers and some other groups. Adults born before 1957 are considered immune.",
        "Infants 6 to 11 months should get one dose before international travel; this does not replace the routine two doses.",
        "One dose is about 93% effective against measles and two doses about 97%.",
      ],
      who: [
        "Two doses. The first is usually given at 9 months where measles is common and at 12 to 15 months elsewhere; the second later in childhood, usually at 15 to 18 months.",
        "The vaccine is often combined with mumps, rubella and/or varicella vaccines. WHO notes rubella is the most common vaccine-preventable infection that can infect babies in the womb.",
      ],
    },
    sources: [
      { label: "WHO measles fact sheet (15 Jul 2026)", url: "https://www.who.int/news-room/fact-sheets/detail/measles" },
      { label: "Australian Immunisation Handbook: measles", url: "https://immunisationhandbook.health.gov.au/contents/vaccine-preventable-diseases/measles" },
      { label: "CDC measles vaccine recommendations", url: "https://www.cdc.gov/measles/hcp/vaccine-considerations" },
      { label: "CDC MMR information for providers", url: "https://www.cdc.gov/vaccines/hcp/by-disease/mmr.html" },
      NIP_SCHEDULE,
    ],
  },
  {
    id: "tuberculosis",
    name: "Tuberculosis (TB)",
    short: "TB",
    headline: "10.7 million ill and 1.23 million deaths in 2024 (WHO)",
    facts: [
      ["Cause", "Mycobacterium tuberculosis bacteria, most often affecting the lungs"],
      ["Spread", "Through the air when a person with TB disease coughs, sneezes or spits. People with TB infection (not disease) are not contagious"],
      ["Burden (2024)", "10.7 million people fell ill (5.8 million men, 3.7 million women, 1.2 million children); 1.23 million died"],
      ["Curable?", "Yes. TB is preventable and curable"],
      ["Vaccine", "BCG; protects young children from severe forms but is not routine in low-incidence countries such as Australia and the US"],
    ],
    sections: [
      {
        heading: "Overview",
        paras: [
          "TB is the world's leading cause of death from a single infectious agent and was also the leading killer of people with HIV in 2024. About a quarter of the global population is estimated to have been infected, but only about 5% to 10% of infected people go on to develop TB disease. Babies and children who are infected are at higher risk of developing disease. WHO estimates global efforts have saved about 83 million lives since 2000. Over 80% of cases and deaths occur in low- and middle-income countries.",
        ],
      },
      {
        heading: "Symptoms",
        paras: [
          "Common symptoms are a prolonged cough (sometimes with blood), chest pain, weakness, fatigue, weight loss, fever and night sweats. Symptoms can be mild for months, so TB can spread without people realising. Some people with TB disease have no symptoms but can still spread it. TB can also affect the kidneys, brain, spine and skin.",
        ],
      },
      {
        heading: "Risk factors",
        paras: [
          "Diabetes, weakened immune system (for example HIV), undernutrition, tobacco use and harmful alcohol use. People living with HIV are 12 times more likely to develop TB disease. In 2024 an estimated 0.97 million new cases were attributable to undernutrition, 0.93 million to diabetes, 0.74 million to alcohol use disorders, 0.70 million to smoking and 0.57 million to HIV.",
        ],
      },
      {
        heading: "Diagnosis and treatment",
        bullets: [
          "WHO recommends rapid molecular or point-of-care tests as the first diagnostic tests for anyone with signs and symptoms.",
          "Infection (without disease) can be identified with a tuberculin skin test, interferon gamma release assay (IGRA) or newer antigen-based skin test.",
          "TB disease is treated with daily antibiotics (rifampicin, isoniazid, pyrazinamide, ethambutol) for 4 to 6 months. Stopping early or without advice is dangerous and can cause drug resistance.",
          "Drug-resistant TB needs different medicines. Only about 2 in 5 people with multidrug-resistant TB accessed treatment in 2024.",
          "TB preventive treatment stops infection from becoming disease and should be completed if prescribed.",
        ],
      },
      {
        heading: "Where TB is concentrated",
        paras: [
          "In 2024 the largest numbers of new cases were in the WHO South-East Asia Region (34%), Western Pacific Region (27%) and African Region (25%). About 87% of cases were in 30 high-burden countries, with India (25%), Indonesia (10%), the Philippines (6.8%), China (6.5%) and Pakistan (6.3%) leading.",
        ],
      },
    ],
    vaccination: {
      au: [
        "BCG is **not part of the routine NIP schedule**.",
        "It is recommended as a single intradermal dose for Aboriginal and Torres Strait Islander neonates living in areas of high TB incidence in the Northern Territory, Queensland and northern South Australia. State and territory programs provide it.",
        "It is also recommended for children under 5 travelling to countries with high TB incidence (more than 40 cases per 100,000 population per year), after discussion with a state or territory TB service, paediatric infectious diseases specialist or travel vaccine centre.",
        "BCG is not as effective in older children and adults, and should be deferred in some groups (for example people being treated for latent TB infection).",
      ],
      us: [
        "BCG is not generally used in the United States. It is given to infants and young children in countries where TB is common and protects against severe forms such as TB meningitis and miliary TB; protection weakens over time.",
        "It can cause a false-positive TB skin test, so TB blood tests (IGRA) are preferred for people who have had BCG.",
        "Pregnant women should not receive BCG.",
      ],
      who: ["In certain countries BCG is given to babies or small children; the vaccine prevents deaths from TB and protects children from serious forms."],
    },
    sources: [
      { label: "WHO tuberculosis fact sheet (24 Mar 2026)", url: "https://www.who.int/news-room/fact-sheets/detail/tuberculosis" },
      { label: "Australian Immunisation Handbook: tuberculosis", url: "https://immunisationhandbook.health.gov.au/contents/vaccine-preventable-diseases/tuberculosis" },
      {
        label: "Handbook: vaccination for Aboriginal and Torres Strait Islander people",
        url: "https://immunisationhandbook.health.gov.au/contents/vaccination-for-special-risk-groups/vaccination-for-aboriginal-and-torres-strait-islander-people",
      },
      { label: "CDC TB vaccine (BCG)", url: "https://www.cdc.gov/tb/vaccines/index.html" },
    ],
  },
  {
    id: "polio",
    name: "Polio",
    short: "Polio",
    headline: "1 in 200 infections causes irreversible paralysis (WHO)",
    facts: [
      ["Cause", "Poliovirus (wild types 1, 2, 3 and vaccine-derived strains)"],
      ["Spread", "Person to person, mainly faecal-oral; less often via contaminated water or food. The virus multiplies in the intestine and can invade the nervous system"],
      ["Incubation", "Usually 7 to 10 days (range 4 to 35)"],
      ["Who is affected", "Mainly children under 5"],
      ["Severity", "1 in 200 infections leads to irreversible paralysis; 5% to 10% of those paralysed die when breathing muscles are affected"],
      ["Cure", "None. Polio can only be prevented by vaccination"],
    ],
    sections: [
      {
        heading: "Overview",
        paras: [
          "Up to 90% of infected people have no or only mild symptoms, so the disease often goes unrecognised. Initial symptoms are fever, fatigue, headache, vomiting, neck stiffness and limb pain. In a small proportion of cases the virus causes paralysis, usually of the legs, which can develop within hours.",
        ],
      },
      {
        heading: "Global progress (WHO)",
        bullets: [
          "Wild poliovirus cases have fallen by over 99% since 1988, from an estimated 350,000 cases in more than 125 endemic countries to two endemic countries: Afghanistan and Pakistan.",
          "Wild poliovirus types 2 and 3 have been declared eradicated; only type 1 remains. The WHO South-East Asia Region was certified polio-free in 2014 and the African Region in 2020.",
          "Vaccine-derived polioviruses can emerge and spread in communities with low immunisation coverage. WHO's Polio IHR Emergency Committee held its 44th meeting in March 2026, and WHO prequalified an additional novel oral polio vaccine in February 2026.",
          "As long as a single child remains infected, children everywhere are at risk.",
        ],
      },
    ],
    vaccination: {
      au: [
        "**Inactivated polio vaccine (IPV) in the hexavalent vaccine** (Infanrix hexa or Vaxelis) at 2, 4 and 6 months.",
        "**DTPa-IPV booster** (Infanrix IPV or Quadracel) at 4 years.",
        "People under 20 who missed doses can catch up under the NIP. Refugees and humanitarian entrants aged 20 and over are eligible for polio catch-up if missed.",
      ],
      us: [
        "Four doses of IPV at 2 months, 4 months, 6 to 18 months and 4 to 6 years. IPV has been the only polio vaccine used in the US since 2000.",
        "Unvaccinated adults should have 3 doses of IPV. Fully vaccinated adults at increased risk (for example some travellers, laboratory and health-care workers) may have one lifetime booster.",
        "Two doses of IPV give at least 90% protection and three doses at least 99%.",
      ],
      who: [
        "WHO and its Global Polio Eradication Initiative partners focus on immunisation and disease surveillance, supporting countries still affected by poliovirus or at high risk of re-emergence.",
        "Eradication requires stopping both wild and vaccine-derived poliovirus.",
      ],
    },
    sources: [
      { label: "WHO poliomyelitis fact sheet", url: "https://www.who.int/news-room/fact-sheets/detail/poliomyelitis" },
      { label: "WHO polio health topic", url: "https://www.who.int/health-topics/poliomyelitis" },
      { label: "CDC polio vaccine recommendations", url: "https://www.cdc.gov/polio/hcp/vaccine-considerations/index.html" },
      NIP_SCHEDULE,
    ],
  },
];

// Appendix B: why the US entries describe the long-standing CDC schedule
export const US_STATUS: string[] = [
  "On 5 January 2026 the CDC Acting Director approved a revised childhood immunization schedule without the usual ACIP process. It reduced the number of diseases with default (routine) recommendations from 17 to 11 by moving some (including hepatitis A, hepatitis B, meningococcal, COVID-19, influenza, rotavirus and RSV) to high-risk or shared clinical decision-making categories, and reduced HPV to a single dose.",
  "On 16 March 2026 a federal court (US District Court, District of Massachusetts, in a case brought by the American Academy of Pediatrics) stayed that schedule, the appointments of 13 ACIP members, and all votes of the reconstituted ACIP after 11 June 2025. The stay mostly reverts schedules to the versions published in January 2025, except for some April and May 2025 recommendations.",
  "On 29 May 2026 Executive Order 14407 directed CDC and ACIP to review the January 2026 schedule. Further court or agency action could change this at any time.",
  "This page therefore describes the long-standing recommendations that CDC web pages currently show for HPV, hepatitis B, MMR, varicella and polio, and notes where the January 2026 revision would differ. For COVID-19, CDC's current 2026 to 2027 guidance applies.",
];
