import { redirect } from "next/navigation";
import { McpDemo } from "./mcp-demo";
import { auth } from "../../(auth)/auth";

export default async function McpPage() {
  const session = await auth();

  if (!session) {
    redirect(`/login?redirectUrl=${encodeURIComponent("/mcp")}`);
  }

  return (
    <div className="flex flex-1 flex-col gap-6 p-4 md:p-8">
      <div className="flex flex-col gap-2">
        <h1 className="text-2xl font-semibold tracking-tight">MCP completion demo</h1>
        <p className="text-muted-foreground text-sm">
          Explore the standalone completion endpoint that merges tool catalogs
          from configured Model Context Protocol transports.
        </p>
      </div>
      <McpDemo />
    </div>
  );
}
