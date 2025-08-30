import Bun from "bun";

const emojis = await Bun.file("emojis.json").json();
const items = emojis.data.vendorHistoricEmoji_v1.items;

const emojinames = []

for (const item of items) {
    for (const image of item.images) {
        emojinames.push(image.slug)
    }
}

Bun.write("./converted.json", JSON.stringify(emojinames))

console.log(emojinames.length)