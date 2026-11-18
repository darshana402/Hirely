console.log("Hirely content script loaded");


// =====================================================
// CLEAN TEXT
// =====================================================

function cleanText(text) {
  if (!text) return null;

  return text
    .replace(/\s+/g, " ")
    .replace(/\s*-\s*job post\s*$/i, "")
    .replace(/\s*\|\s*LinkedIn.*$/i, "")
    .replace(/\s*-\s*LinkedIn.*$/i, "")
    .replace(/\s*\|\s*Indeed.*$/i, "")
    .trim();
}


// =====================================================
// GET FIRST VALID TEXT
// =====================================================

function getFirstText(selectors, parent = document) {

  for (const selector of selectors) {

    const elements = parent.querySelectorAll(selector);

    for (const element of elements) {

      const text = element.innerText?.trim();

      if (text) {
        return cleanText(text);
      }
    }
  }

  return null;
}


// =====================================================
// LINKEDIN
// =====================================================

function getLinkedInJob() {

  const title = document.title
    ?.split("|")[0]
    ?.trim();

  const company = getFirstText([
    ".job-details-jobs-unified-top-card__company-name",
    ".job-details-jobs-unified-top-card__primary-description a"
  ]);

  return {
    title: cleanText(title),
    company: cleanText(company)
  };
}
// =====================================================
// INDEED
// =====================================================

function getIndeedJob() {

  // ===================================================
  // JOB TITLE
  // ===================================================

  const titleElement = document.querySelector(
    '[data-testid="jobsearch-JobInfoHeader-title"]'
  );

  let title = null;

  if (titleElement) {

    // Get only the visible title text
    title = titleElement.innerText?.trim();

    // Remove "- job post" if Indeed includes it
    title = cleanText(title);

  } else {

    console.log(
      "Hirely: Indeed job title element not found"
    );
  }


  // ===================================================
  // COMPANY
  // ===================================================

  const companyElement = document.querySelector(
    '[data-testid="inlineHeader-companyName"]'
  );

  let company = null;

  if (companyElement) {
    company = cleanText(
      companyElement.innerText?.trim()
    );
  } else {

    console.log(
      "Hirely: Indeed company element not found"
    );
  }


  // ===================================================
  // DEBUG
  // ===================================================

  console.log(
    "Hirely Indeed extracted title:",
    title
  );

  console.log(
    "Hirely Indeed extracted company:",
    company
  );


  return {
    title,
    company
  };
}

// =====================================================
// GENERIC JOB WEBSITE
// =====================================================

function getGenericJob() {

  const title = getFirstText([
    "[data-testid='job-title']",
    "[data-testid='jobTitle']",
    ".job-title",
    ".job-title h1",
    ".job-header h1",
    ".job-details h1",
    "[class*='job-title']",
    "[class*='jobTitle']"
  ]);


  const company = getFirstText([
    "[data-testid='company-name']",
    "[data-testid='companyName']",
    ".company-name",
    ".job-company",
    "[class*='company-name']",
    "[class*='companyName']"
  ]);


  return {
    title,
    company
  };
}


// =====================================================
// FALLBACK TITLE FROM REAL HEADINGS
// =====================================================

function findJobTitleFromHeading() {

  const headings = document.querySelectorAll(
    "h1, h2, [role='heading']"
  );


  const ignoredTitles = [
    "jobs",
    "job details",
    "job description",
    "about the job",
    "about us",
    "similar jobs",
    "related jobs",
    "recommended jobs",
    "login",
    "sign up",
    "apply now",
    "job search",
    "job search india",
    "jobs in india"
  ];


  for (const element of headings) {

    const text = cleanText(element.innerText);

    if (!text) continue;

    if (text.length > 150) continue;

    if (
      ignoredTitles.includes(
        text.toLowerCase()
      )
    ) {
      continue;
    }


    return text;
  }


  return null;
}


// =====================================================
// COMPANY FALLBACK
// =====================================================

function findCompanyFallback(pageText) {

  if (!pageText) {
    return null;
  }


  const companyPatterns = [
    /Xcelore\s+Pvt\s+Ltd/i
  ];


  for (const pattern of companyPatterns) {

    const match = pageText.match(pattern);

    if (match) {
      return match[0].trim();
    }
  }


  return null;
}


// =====================================================
// MAIN JOB EXTRACTION
// =====================================================

function getJobPageContent() {

  const hostname =
    window.location.hostname.toLowerCase();


  let title = null;
  let company = null;


  // ===================================================
  // INDEED
  // ===================================================

  if (hostname.includes("indeed.com")) {

    const result = getIndeedJob();

    title = result.title;
    company = result.company;
  }


  // ===================================================
  // LINKEDIN
  // ===================================================

  else if (hostname.includes("linkedin.com")) {

    const result = getLinkedInJob();

    title = result.title;
    company = result.company;
  }


  // ===================================================
  // OTHER JOB WEBSITES
  // ===================================================

  else {

    const result = getGenericJob();

    title = result.title;
    company = result.company;
  }


  // ===================================================
  // FALLBACK TITLE
  // ===================================================

  if (!title) {

    title = findJobTitleFromHeading();
  }


  // ===================================================
  // PAGE TEXT
  // ===================================================

  const pageText =
    document.body?.innerText || "";


  // ===================================================
  // FALLBACK COMPANY
  // ===================================================

  if (!company) {

    company =
      findCompanyFallback(pageText);
  }


  // ===================================================
  // DOCUMENT TITLE FALLBACK
  // ===================================================

  /*
   * Only use document.title on non-Indeed websites.
   *
   * We intentionally DO NOT use it for Indeed because
   * Indeed may return something generic such as:
   *
   * "Job Search India"
   */

  if (
    !title &&
    !hostname.includes("indeed.com")
  ) {

    title =
      cleanText(document.title);
  }


  // ===================================================
  // FINAL CLEANING
  // ===================================================

  title =
    cleanText(title);


  // ===================================================
  // DEBUG LOGS
  // ===================================================

  console.log(
    "Hirely extracted title:",
    title
  );

  console.log(
    "Hirely extracted company:",
    company
  );

  console.log(
    "Hirely current URL:",
    window.location.href
  );


  // ===================================================
  // RETURN JOB DATA
  // ===================================================

  return {

    title:
      title || "Unknown Job",

    company:
      company || null,

    url:
      window.location.href,

    text:
      pageText

  };
}


// =====================================================
// LISTEN FOR REQUEST FROM EXTENSION
// =====================================================

chrome.runtime.onMessage.addListener(
  (message, sender, sendResponse) => {

    if (message.type === "GET_JOB_CONTENT") {

      try {

        const jobContent =
          getJobPageContent();


        sendResponse({

          success: true,

          data: jobContent

        });

      } catch (error) {

        console.error(
          "Hirely extraction error:",
          error
        );


        sendResponse({

          success: false,

          error: error.message

        });
      }
    }


    return true;
  }
);

