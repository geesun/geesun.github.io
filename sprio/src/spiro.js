var wSize = 0;
var bigGearSize = 0; 
var smallGearSize = 0; 
var bgColor = 255;
var outerAngle = 0; 
var rotateAngle = 0.01;
var innerAngle = 0;
var holeOffset = 0;
var penColor; 
var reSize = 0; 
var speed = 3;
var start = 1; 

function genGearSize() {
    wSize = windowWidth * 0.8; 
    if (wSize  > windowHeight){
        wSize = windowHeight * 0.8;
    }
    bigGearSize = wSize * 0.8 * 0.5;

    smallGearSize = bigGearSize * random(0.7);
    holeOffset = smallGearSize * 0.467;
}

function initCanvas(){
    smooth()
    background(bgColor);
    strokeWeight(3);
    
    smallGearLayer = createGraphics(wSize ,wSize  );
    spiroLayer = createGraphics(wSize ,wSize  );
    
}

function onClear()
{
  reSize = 1;
}

function onChangeGearSize() 
{
  var s = document.getElementById("gearSize").value;
  smallGearSize = s/100.00 * bigGearSize;
  reSize = 1;
}

function onChangeHole()
{
  var h = document.getElementById("hole").value;
  holeOffset = h/100.00 * smallGearSize;
  reSize = 1;
}

function onSave()
{
  save(spiroLayer,"万花尺.png")
}

function windowResized() {
    genGearSize();
    resizeCanvas(wSize,wSize);
    initCanvas();
}

function onChangeSpeed()
{
  speed = document.getElementById("speed").value;
}

function onChangeColor()
{
  penColor = document.getElementById("color").value;
 
}

function onStart()
{
  if(start){
    start = 0 ;
    document.getElementById('start').innerHTML="开始";
  }else{
    start = 1; 
    document.getElementById('start').innerHTML="停止";
  }
}

function setup()
{
    genGearSize();
    var canvas = createCanvas(wSize,wSize);
    canvas.parent('sketch-holder');
    initCanvas();
    penColor = color(255, 0, 0);

}

function draw()
{
    if(reSize == 1){
        initCanvas();
        reSize = 0;
    }

    smallGearLayer.push();
    smallGearLayer.background(255);
    smallGearLayer.noFill();
    smallGearLayer.strokeWeight(3);
    smallGearLayer.translate(wSize/2,wSize/2);
    smallGearLayer.ellipse(0,0,bigGearSize * 2 - 10,bigGearSize * 2 - 10);
    smallGearLayer.rotate(outerAngle); 
    smallGearLayer.translate((bigGearSize - smallGearSize), 0); 
    smallGearLayer.rotate(innerAngle);
    smallGearLayer.ellipse(0,0,smallGearSize * 2 - 10,smallGearSize * 2- 10);
    smallGearLayer.ellipse(holeOffset,0,5,5);
    smallGearLayer.pop();

    if(start == 1){
      for (var i = 0; i < speed; i++){
          spiroLayer.push();
          spiroLayer.translate(wSize/2,wSize/2);
          spiroLayer.rotate(outerAngle); 
          spiroLayer.translate((bigGearSize - smallGearSize), 0);
          spiroLayer.rotate(innerAngle);
          spiroLayer.fill(penColor);
          spiroLayer.stroke(penColor);
          spiroLayer.strokeWeight(3);
          spiroLayer.point(holeOffset,0);
          spiroLayer.pop(); 

          outerAngle += rotateAngle;
          innerAngle = -outerAngle * bigGearSize/smallGearSize;
      }
    }

    rect(0,0,wSize,wSize);
    image(smallGearLayer,0,0)
    image(spiroLayer,0,0)
}

