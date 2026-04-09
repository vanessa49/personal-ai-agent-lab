'use strict';
const fs = require('fs');

const data = JSON.parse(fs.readFileSync('squad_conversations.json','utf8'));

if (!fs.existsSync('squad_data')) {
  fs.mkdirSync('squad_data');
}

let count = 0;

for (const convo of data.slice(0,3000)) {   // 只取3000条
  const file = `squad_data/convo_${count}.json`;

  fs.writeFileSync(
    file,
    JSON.stringify({messages: convo.messages}, null, 2)
  );

  count++;
}

console.log("created files:", count);