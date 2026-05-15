import { HubLogin } from "@/components/hub-login";

function readShowSystemManager(): boolean {
  const v = process.env.NEXT_PUBLIC_SHOW_SYSTEM_MANAGER?.trim().toLowerCase();
  if (v === "false") return false;
  return true;
}

export default function Page() {
  return <HubLogin showSystemManager={readShowSystemManager()} />;
}
