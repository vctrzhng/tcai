// make_docx.js -- (re)generate the two DOCX mock contracts.
// Run AFTER make_pdfs.py (which writes generators/docx_content.json).
//   npm install -g docx
//   node generators/make_docx.js
const fs = require("fs");
const path = require("path");
const { Document, Packer, Paragraph, TextRun, AlignmentType, HeadingLevel } = require("docx");

const HERE = __dirname;
const REPO_ROOT = path.dirname(HERE);
const OUT = path.join(REPO_ROOT, "mock_contracts");

const content = JSON.parse(fs.readFileSync(path.join(HERE, "docx_content.json"), "utf8"));

const styles = {
  default: { document: { run: { font: "Times New Roman", size: 21 } } },
  paragraphStyles: [
    { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
      run: { size: 22, bold: true, font: "Times New Roman" },
      paragraph: { spacing: { before: 180, after: 120 }, outlineLevel: 1 } },
  ],
};

for (const [key, c] of Object.entries(content)) {
  const children = [];
  children.push(new Paragraph({
    alignment: AlignmentType.CENTER, spacing: { after: 240 },
    children: [new TextRun({ text: c.title, bold: true, size: 30 })],
  }));
  for (const [heading, body] of c.sections) {
    if (heading) {
      children.push(new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun(heading)] }));
    }
    children.push(new Paragraph({
      alignment: AlignmentType.JUSTIFIED, spacing: { after: 120, line: 300 },
      children: [new TextRun(body)],
    }));
  }
  const doc = new Document({
    styles,
    sections: [{
      properties: { page: { size: { width: 12240, height: 15840 },
        margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } } },
      children,
    }],
  });
  Packer.toBuffer(doc).then((b) => {
    fs.writeFileSync(path.join(OUT, `${key}.docx`), b);
    console.log("wrote", path.join(OUT, `${key}.docx`));
  });
}
