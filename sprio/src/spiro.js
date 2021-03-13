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
var speed = 1;
var start = 1; 
var clearAction = 1;

function genGearSize() {
    wSize = windowWidth * 0.9; 
    if (wSize  > windowHeight){
        wSize = windowHeight * 0.9;
    }
    bigGearSize = wSize * 0.9 * 0.5;

    smallGearSize = bigGearSize * (random(0.5) + 0.2);//0.6;
    holeOffset = smallGearSize * 0.467;
}

function initCanvas(){
    smooth()
    background(bgColor);
    strokeWeight(3);
    
    gearLayer = createGraphics(wSize ,wSize  );
    if(clearAction == 1){
      spiroLayer = createGraphics(wSize ,wSize);
      clearAction = 0;
    }
    
}

function onClear()
{
  reSize = 1;
  clearAction = 1;
}

function onChangeGearSize() 
{
  var s = document.getElementById("gearSize").value;
  smallGearSize = s/100.00 * bigGearSize;
  if(smallGearSize < 30){
    smallGearSize = 30;
  }
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

    gearLayer.push();
    gearLayer.background(255);
    gearLayer.fill(240);
    gearLayer.strokeWeight(3);
    gearLayer.rect(0,0,wSize,wSize);
    gearLayer.noFill();
    gearLayer.translate(wSize/2,wSize/2);
    gearLayer.ellipse(0,0,bigGearSize * 2 - 10,bigGearSize * 2 - 10);
    gearLayer.rotate(outerAngle); 
    gearLayer.translate((bigGearSize - smallGearSize), 0); 
    gearLayer.rotate(innerAngle);
    gearLayer.ellipse(0,0,smallGearSize * 2 - 10,smallGearSize * 2- 10);
    gearLayer.ellipse(holeOffset,0,5,5);
    gearLayer.pop();

    if(start == 1){
      for (var i = 0; i < speed; i++){
          spiroLayer.push();
          spiroLayer.translate(wSize/2,wSize/2);
          spiroLayer.rotate(outerAngle); 
          spiroLayer.translate((bigGearSize - smallGearSize), 0);
          spiroLayer.rotate(innerAngle);
          spiroLayer.fill(penColor);
          spiroLayer.stroke(penColor);
          spiroLayer.strokeWeight(1.5);
          spiroLayer.point(holeOffset,0);
          spiroLayer.pop(); 

          outerAngle += rotateAngle;
          innerAngle = -outerAngle * bigGearSize/smallGearSize;
      }
    }

    
    image(gearLayer,0,0)
    image(spiroLayer,0,0)
}

