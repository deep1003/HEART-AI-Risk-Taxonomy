import fs from "node:fs/promises";
import { FileBlob, SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const repo = new URL("..", import.meta.url).pathname.replace(/\/$/, "");
const sourceCsv = `${repo}/data/heart_l4_risk_cards.csv`;
const dictionaryCsv = `${repo}/data/data_dictionary.csv`;
const output = `${repo}/data/HEART_L4_Risk_Cards.xlsx`;

const workbook = await Workbook.fromCSV(await fs.readFile(sourceCsv, "utf8"), { sheetName: "Risk Cards" });
const cards = workbook.worksheets.getItem("Risk Cards");
cards.freezePanes.freezeRows(1);
cards.freezePanes.freezeColumns(1);
cards.showGridLines = false;
const used = cards.getUsedRange();
used.format.font = { name: "Aptos", size: 10, color: "#14213D" };
used.format.verticalAlignment = "top";
used.format.wrapText = true;
const header = cards.getRange("A1:AD1");
header.format.fill = "#2457D6";
header.format.font = { name: "Aptos", size: 10, bold: true, color: "#FFFFFF" };
header.format.rowHeight = 34;
header.format.verticalAlignment = "center";
used.format.borders = { preset: "all", style: "thin", color: "#DCE4EF" };
cards.getRange("A:A").format.columnWidth = 18;
cards.getRange("B:C").format.columnWidth = 30;
cards.getRange("D:L").format.columnWidth = 20;
cards.getRange("M:N").format.columnWidth = 52;
cards.getRange("O:P").format.columnWidth = 16;
cards.getRange("Q:V").format.columnWidth = 28;
cards.getRange("W:W").format.columnWidth = 70;
cards.getRange("X:AB").format.columnWidth = 25;
cards.getRange("AC:AD").format.columnWidth = 14;
cards.getRange("AC2:AD623").format.fill = "#F4F7FB";
cards.getRange("AC2:AD623").format.numberFormat = "General";

const dictWorkbook = await Workbook.fromCSV(await fs.readFile(dictionaryCsv, "utf8"), { sheetName: "Data Dictionary" });
const dictionarySource = dictWorkbook.worksheets.getItem("Data Dictionary").getUsedRange();
const dictionary = workbook.worksheets.add("Data Dictionary");
dictionary.getRange("A1:D31").copyFrom(dictionarySource, "values");
dictionary.freezePanes.freezeRows(1);
dictionary.showGridLines = false;
dictionary.getUsedRange().format.font = { name: "Aptos", size: 10, color: "#14213D" };
dictionary.getUsedRange().format.wrapText = true;
dictionary.getUsedRange().format.verticalAlignment = "top";
dictionary.getRange("A1:D1").format.fill = "#12736A";
dictionary.getRange("A1:D1").format.font = { name: "Aptos", size: 10, bold: true, color: "#FFFFFF" };
dictionary.getRange("A1:D31").format.borders = { preset: "all", style: "thin", color: "#DCE4EF" };
dictionary.getRange("A:A").format.columnWidth = 31;
dictionary.getRange("B:B").format.columnWidth = 72;
dictionary.getRange("C:D").format.columnWidth = 23;

const validation = workbook.worksheets.add("Validation");
validation.showGridLines = false;
validation.getRange("A1:B9").values = [
  ["HEART L4 Risk Card Dataset", "Validation record"],
  ["Metric", "Result"],
  ["Total L4 cards", 622],
  ["L3 categories", 47],
  ["General AI cards", 492],
  ["Agentic AI cards", 67],
  ["Physical AI cards", 63],
  ["Evidence references and quotations", "622 of 622"],
  ["Probability and Severity", "Reserved and intentionally blank"],
];
validation.getRange("A1:B1").format.fill = "#14213D";
validation.getRange("A1:B1").format.font = { name: "Aptos Display", size: 16, bold: true, color: "#FFFFFF" };
validation.getRange("A2:B2").format.fill = "#2457D6";
validation.getRange("A2:B2").format.font = { name: "Aptos", size: 10, bold: true, color: "#FFFFFF" };
validation.getRange("A1:B9").format.borders = { preset: "all", style: "thin", color: "#DCE4EF" };
validation.getRange("A1:B9").format.wrapText = true;
validation.getRange("A:A").format.columnWidth = 42;
validation.getRange("B:B").format.columnWidth = 42;

await workbook.recalculate();
const inspection = await workbook.inspect({ kind: "sheet", include: "id,name", maxChars: 3000 });
console.log(inspection.ndjson);
const exported = await SpreadsheetFile.exportXlsx(workbook);
await exported.save(output);
console.log(output);
