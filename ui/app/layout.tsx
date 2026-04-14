import type { Metadata, Viewport } from "next";
import { JetBrains_Mono } from "next/font/google";
import { AuthProvider } from "@/lib/auth";
import Providers from "./providers";
import "./globals.css";

const mono = JetBrains_Mono({
  variable: "--font-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: {
    default: "CartWise",
    template: "%s | CartWise",
  },
  description: "Grocery cost splitting with meal planning",
  appleWebApp: {
    capable: true,
    statusBarStyle: "default",
    title: "CartWise",
  },
  openGraph: {
    title: "CartWise",
    description: "Grocery cost splitting with meal planning",
    type: "website",
  },
};

export const viewport: Viewport = {
  themeColor: "#ffffff",
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${mono.variable} h-full`}>
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          rel="stylesheet"
          href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200&display=swap"
        />
      </head>
      <body className="min-h-full flex flex-col font-mono bg-white text-black">
        <Providers>
          <AuthProvider>{children}</AuthProvider>
        </Providers>
      </body>
    </html>
  );
}
