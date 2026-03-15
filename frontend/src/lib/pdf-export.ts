/**
 * PDF Export Utility for HealthOS
 * Uses jsPDF + jspdf-autotable for generating downloadable reports
 */

interface ReportSection {
  title: string;
  content?: string;
  table?: {
    headers: string[];
    rows: string[][];
  };
}

interface ReportConfig {
  title: string;
  subtitle?: string;
  generatedBy?: string;
  sections: ReportSection[];
  filename?: string;
}

export async function generatePDF(config: ReportConfig): Promise<void> {
  // Dynamic import to avoid SSR issues
  const { default: jsPDF } = await import("jspdf");
  const autoTableModule = await import("jspdf-autotable");
  // jspdf-autotable adds itself to jsPDF prototype via side-effect import

  const doc = new jsPDF({ orientation: "portrait", unit: "mm", format: "a4" });
  const pageWidth = doc.internal.pageSize.getWidth();
  let y = 20;

  // Header background
  doc.setFillColor(19, 107, 250); // healthos-600
  doc.rect(0, 0, pageWidth, 40, "F");

  // Title
  doc.setTextColor(255, 255, 255);
  doc.setFontSize(22);
  doc.setFont("helvetica", "bold");
  doc.text(config.title, 14, 18);

  if (config.subtitle) {
    doc.setFontSize(11);
    doc.setFont("helvetica", "normal");
    doc.text(config.subtitle, 14, 26);
  }

  // Meta info
  doc.setFontSize(9);
  doc.text(`Generated: ${new Date().toLocaleString()}`, 14, 34);
  if (config.generatedBy) {
    doc.text(`By: ${config.generatedBy}`, pageWidth - 14, 34, { align: "right" });
  }

  // Eminence HealthOS branding
  doc.text("Eminence HealthOS", pageWidth - 14, 18, { align: "right" });

  y = 50;

  // Sections
  for (const section of config.sections) {
    // Check if we need a new page
    if (y > 260) {
      doc.addPage();
      y = 20;
    }

    // Section title
    doc.setTextColor(17, 39, 89); // healthos-950
    doc.setFontSize(14);
    doc.setFont("helvetica", "bold");
    doc.text(section.title, 14, y);
    y += 2;

    // Underline
    doc.setDrawColor(19, 107, 250);
    doc.setLineWidth(0.5);
    doc.line(14, y, 80, y);
    y += 8;

    // Text content
    if (section.content) {
      doc.setTextColor(55, 65, 81); // gray-700
      doc.setFontSize(10);
      doc.setFont("helvetica", "normal");
      const lines = doc.splitTextToSize(section.content, pageWidth - 28);
      doc.text(lines, 14, y);
      y += lines.length * 5 + 6;
    }

    // Table
    if (section.table) {
      const autoTable = (autoTableModule as unknown as { default?: (doc: jsPDF, opts: Record<string, unknown>) => void }).default || autoTableModule;
      if (typeof autoTable === "function") {
        autoTable(doc, {
          startY: y,
          head: [section.table.headers],
          body: section.table.rows,
          margin: { left: 14, right: 14 },
          styles: { fontSize: 9, cellPadding: 3 },
          headStyles: {
            fillColor: [19, 107, 250],
            textColor: 255,
            fontStyle: "bold",
          },
          alternateRowStyles: { fillColor: [238, 247, 255] },
          theme: "grid",
        });
      }
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      y = (doc as any).lastAutoTable?.finalY + 10 || y + 40;
    }

    y += 4;
  }

  // Footer on all pages
  const totalPages = doc.getNumberOfPages();
  for (let i = 1; i <= totalPages; i++) {
    doc.setPage(i);
    doc.setFontSize(8);
    doc.setTextColor(156, 163, 175); // gray-400
    doc.text(
      `Eminence HealthOS — Confidential — Page ${i} of ${totalPages}`,
      pageWidth / 2,
      doc.internal.pageSize.getHeight() - 8,
      { align: "center" }
    );
  }

  // Download
  const filename = config.filename || `${config.title.replace(/\s+/g, "_")}_${new Date().toISOString().split("T")[0]}.pdf`;
  doc.save(filename);
}

// Convenience helpers for common report types
export function exportPatientReport(patient: {
  name: string;
  id: string;
  conditions: string[];
  medications: string[];
  vitals: { label: string; value: string; date: string }[];
}) {
  return generatePDF({
    title: `Patient Report — ${patient.name}`,
    subtitle: `Patient ID: ${patient.id}`,
    sections: [
      {
        title: "Active Conditions",
        content: patient.conditions.join(", ") || "None recorded",
      },
      {
        title: "Current Medications",
        content: patient.medications.join(", ") || "None recorded",
      },
      {
        title: "Recent Vitals",
        table: {
          headers: ["Vital", "Value", "Date"],
          rows: patient.vitals.map((v) => [v.label, v.value, v.date]),
        },
      },
    ],
  });
}

export function exportComplianceReport(data: {
  score: number;
  framework: string;
  findings: { category: string; status: string; details: string }[];
}) {
  return generatePDF({
    title: `${data.framework} Compliance Report`,
    subtitle: `Overall Score: ${data.score}%`,
    sections: [
      {
        title: "Compliance Summary",
        content: `The organization achieved a compliance score of ${data.score}% against ${data.framework} requirements. ${
          data.score >= 90
            ? "This score meets regulatory thresholds."
            : "Remediation is recommended for non-compliant areas."
        }`,
      },
      {
        title: "Detailed Findings",
        table: {
          headers: ["Category", "Status", "Details"],
          rows: data.findings.map((f) => [f.category, f.status, f.details]),
        },
      },
    ],
  });
}

export function exportAnalyticsReport(data: {
  title: string;
  metrics: { label: string; value: string; trend: string }[];
  tableData?: { headers: string[]; rows: string[][] };
}) {
  const sections: ReportSection[] = [
    {
      title: "Key Metrics",
      table: {
        headers: ["Metric", "Value", "Trend"],
        rows: data.metrics.map((m) => [m.label, m.value, m.trend]),
      },
    },
  ];
  if (data.tableData) {
    sections.push({ title: "Detailed Data", table: data.tableData });
  }
  return generatePDF({ title: data.title, sections });
}
