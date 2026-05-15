import SystemManagerShell from "@/components/system-manager/system-manager-shell";

export default function SystemManagerLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return <SystemManagerShell>{children}</SystemManagerShell>;
}
