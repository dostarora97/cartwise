import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "CartWise",
    short_name: "CartWise",
    description: "Grocery cost splitting with meal planning",
    start_url: "/",
    display: "standalone",
    background_color: "#09090b",
    theme_color: "#09090b",
    icons: [],
    share_target: {
      action: "/invoice",
      method: "POST",
      enctype: "multipart/form-data",
      params: {
        files: [
          {
            name: "invoice",
            accept: ["application/pdf", ".pdf"],
          },
        ],
      },
    },
  };
}
