import * as vscode from "vscode";

export function activate(context: vscode.ExtensionContext) {
  context.subscriptions.push(
    vscode.commands.registerCommand("gie.scan", async () => {
      const cfg = vscode.workspace.getConfiguration("gie");
      vscode.window.showInformationMessage(`GIE scan via ${cfg.get("gie.baseUrl") || cfg.get("baseUrl")}`);
    }),
    vscode.commands.registerCommand("gie.connect", async () => {
      const base = vscode.workspace.getConfiguration("gie").get<string>("baseUrl") || "http://localhost:8090";
      const res = await fetch(`${base}/v1/integrations`);
      const data = await res.json();
      vscode.window.showInformationMessage(`GIE platforms: ${data?.data?.count ?? "?"}`);
    })
  );
}

export function deactivate() {}
