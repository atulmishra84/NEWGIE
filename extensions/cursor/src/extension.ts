import * as vscode from "vscode";

export function activate(context: vscode.ExtensionContext) {
  context.subscriptions.push(
    vscode.commands.registerCommand("gie.cursor.connect", async () => {
      const base = vscode.workspace.getConfiguration("gie").get<string>("baseUrl") || "http://localhost:8090";
      await fetch(`${base}/v1/integrations/connect`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "x-tenant-id": "default" },
        body: JSON.stringify({
          tenant_id: "default",
          platform_id: "cursor",
          name: "cursor-workspace",
          auth_method: "api_key",
          credentials: { api_key: "cursor-dev" },
        }),
      });
      vscode.window.showInformationMessage("Connected Cursor to GIE");
    })
  );
}

export function deactivate() {}
