import "./globals.css";

export const metadata = {
  title: "Agent Studio",
  description: "Define agents, run them, review the drafts.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
