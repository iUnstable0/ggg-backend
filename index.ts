import Bun from "bun";
import fs from "node:fs";

let urlprefix = "https://em-content.zobj.net/" //source/apple/419/grinning-face_1f600.png

const emojis = await (Bun.file("./emojis.json")).json();
const items = emojis.data.vendorHistoricEmoji_v1.items;

let total = 0;

for (const item of items) {
    console.log(item.images.length)

    total += item.images.length

    if (!item.category) {
        fs.mkdirSync("./emojis/uncategorized", { recursive: true });
    } else {
        fs.mkdirSync("./emojis/" + item.category.slug, {recursive: true});
    }
    //
    // if (item.category.slug !== "people") {
    //     continue;
    // }

    let count = 1;
    for (const img of item.images) {
        if (item.category) {
            if (fs.existsSync("./emojis/" + item.category.slug + "/" + img.slug + ".png")) {
                console.log(`SKIPPING: ${img.slug} (${count}/${item.images.length})`);
                count++;
                continue;
            }
        } else {
            if (fs.existsSync("./emojis/uncategorized/" + img.slug + ".png")) {
                console.log(`SKIPPING: ${img.slug} (${count}/${item.images.length})`);
                count++;
                continue;
            }
        }

        console.log(`DOWNLOADING: ${img.slug} (${count}/${item.images.length})`);

        const response = await fetch(urlprefix + img.image.source);
        const arrayBuffer = await response.arrayBuffer();
        const buffer = Buffer.from(arrayBuffer);

        if (!item.category) {
            fs.writeFileSync("./emojis/uncategorized/" + img.slug + ".png", buffer);
        } else {
            fs.writeFileSync("./emojis/" + item.category.slug + "/" + img.slug + ".png", buffer);
        }

        console.log(`SAVED: ${img.slug} (${count}/${item.images.length})`);
        count++;
    }
}

console.log("Total emojis:", total)

