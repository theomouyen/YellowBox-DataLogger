#define PY_SSIZE_T_CLEAN
#define _XOPEN_SOURCE 700

#include <Python.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <fcntl.h>
#include <string.h>
#include <unistd.h>
#include <inttypes.h>
#include <sys/ioctl.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <linux/i2c-dev.h>
#include <wiringPi.h>
#include <softTone.h>
#include "BME68x-Sensor-API/bme68x.h"
#include "BME68x-Sensor-API/bme68x_defs.h"

#define SAMPLE_COUNT  UINT16_C(300)

#define TIMEZONE "TZ=Europe/Berlin"
#define I2C_PORT "/dev/i2c-1"
#define AMB_TEMP 22.0f

#define GRN 17
#define YLW 27
#define RED 22
#define BUZ 16
#define FREQ 440

static int linux_device_handle;
struct bme68x_dev bme;
struct bme68x_conf conf;
struct bme68x_heatr_conf heatr_conf;
struct bme68x_data data;
uint32_t del_period;
uint32_t time_ms = 0;
uint8_t n_fields;
uint16_t sample_count = 1;

// FUNCTIONS
int i2c_open(int *ldh){
    *ldh = open(I2C_PORT, O_RDWR);
    if (*ldh < 0){
        perror("i2c_open");
    }
    return *ldh;
}

int i2c_set_address(int *ldh, uint8_t *addr){
    int option;
    printf("Choose I2C adress\nEnter 0 for 0x76\nEnter 1 for 0x77\n");
    scanf("%d", &option);
    if (option < 1){
        if (ioctl(*ldh, I2C_SLAVE, BME68X_I2C_ADDR_LOW) < 0) {
		perror("i2c_set_adress");
		return -1;
	    }
        *addr = BME68X_I2C_ADDR_LOW;
    }
    else{
       if (ioctl(*ldh, I2C_SLAVE, BME68X_I2C_ADDR_HIGH) < 0) {
		perror("i2c_set_adress");
		return -1;
	    }
        *addr = BME68X_I2C_ADDR_HIGH;
    }
    printf("I2C address is set to %#0x\n", *addr);
    return 0;
}

int i2c_close(int *ldh){
    close(*ldh);
    return 0;
} 

void pi3g_check_connection(int *ldh, uint8_t regAddr, uint8_t *regData, uint16_t len){
 	if (write(*ldh, &regAddr, 1) != 1) {
		perror("pi3g_check_connection");
	}
	if (read(*ldh, regData, len) != len) {
		perror("pi3g_check_connection");
	}
} 

int8_t pi3g_i2c_init(int *ldh, uint8_t *i2c_addr, uint8_t *chip_id){
    printf("linux_device_handle = %d\n", i2c_open(ldh));

    if (!i2c_set_address(ldh, i2c_addr)){
        pi3g_check_connection(ldh, BME68X_REG_CHIP_ID, chip_id, 1);
    }
    if (BME68X_CHIP_ID == *chip_id){
        printf("EXPECTED CHIP ID = %#0x\nACTUAL CHIP ID = %#0x\nBME68X is connected\n\n", BME68X_CHIP_ID, *chip_id);
    } 
    else{
        printf("BME68X is not connected\n\n");
        exit(-1);
    } 
    return 0;
} 

void pi3g_wiringPi_init() {
    wiringPiSetupGpio();

    pinMode(RED, OUTPUT);
    pinMode(YLW, OUTPUT);
    pinMode(GRN, OUTPUT);
    softToneCreate(BUZ);
}

void pi3g_delay_us(uint32_t duration_us, void *intf_ptr) {
    // from wiringPi
    delayMicroseconds(duration_us);
}

int8_t pi3g_read(uint8_t regAddr, uint8_t *regData, uint32_t len, void *intf_ptr) {
    int8_t rslt = BME68X_OK;

 	if (write(linux_device_handle, &regAddr, 1) != 1) {
		perror("pi3g_read register");
		rslt = -1;
	}
	if (read(linux_device_handle, regData, len) != len) {
		perror("pi3g_read data");
		rslt = -1;
	}

    return rslt;
}

int8_t pi3g_write(uint8_t regAddr, const uint8_t *regData, uint32_t len, void *intf_ptr) {
    int8_t rslt = BME68X_OK;
	uint8_t reg[len+1];
    reg[0]=regAddr;
	
    for (int i=1; i<len+1; i++)
       reg[i] = regData[i-1];

    if (write(linux_device_handle, reg, len+1) != len+1) {
		perror("pi3g_write");
		rslt = -1;
	}

    return rslt;
}

// PYTHON
static PyObject *bmeError;
static char bme_docstring[] = "Python interface for BME68X";

// Initialize I2C and BME68X
static PyObject *bme_init(PyObject *self, PyObject *args) {
    const char *i2c_port;
    const int i2c_addr;

    wiringPiSetupGpio();
    putenv(TIMEZONE);

    if (!PyArg_ParseTuple(args, "si", &i2c_port, &i2c_addr)) {
        printf("Wrong arguments in init, string i2c_port, int i2c_addr\n");
        return NULL;
    }

    linux_device_handle = open(i2c_port, O_RDWR);
    if (linux_device_handle < 0) {
        perror("i2c_open");
        exit(linux_device_handle);
    }

    if (ioctl(linux_device_handle, I2C_SLAVE, i2c_addr) < 0) {
    perror("i2c_set_addr");
    exit(-1);
    }
    
    // Initialize BME68X sensor
    bme.intf = BME68X_I2C_INTF;
    bme.amb_temp = AMB_TEMP;
    bme.read = pi3g_read;
    bme.write = pi3g_write;
    bme.delay_us = pi3g_delay_us;
    
    int8_t init_rslt = BME68X_OK;
    init_rslt = bme68x_init(&bme);
    if (init_rslt == BME68X_OK){
        // printf("BME68X is initialized\n");
        if (bme.variant_id == BME68X_VARIANT_GAS_LOW) {
            // printf("Variant = BME68X_VARIANT_GAS_LOW\n");
        } 
        else{
            // printf("Variant = BME68X_VARIANT_GAS_HIGH\n");
        } 
    } 
    else{
        perror("initialize BME68X");
        exit(-1);
    } 

    return Py_BuildValue("s", "Initialized I2C and BME68X");
} 

// Initialize wiringPi
static PyObject *bme_wiringPi_init(PyObject *self, PyObject *args) {
    wiringPiSetupGpio();

    pinMode(RED, OUTPUT);
    pinMode(YLW, OUTPUT);
    pinMode(GRN, OUTPUT);
    softToneCreate(BUZ);

    return Py_BuildValue("s", "Initialized GPIO Pins\nRED = 22, YLW = 27, GRN 17, BUZ = 16");
}

// Set timezone
static PyObject *bme_set_timezone(PyObject *self, PyObject *args) {

    char *timezone;

    if (!PyArg_ParseTuple(args, "s", &timezone)) {
        printf("Wrong arguments in set_timezone, string timezone");
    }

    // printf("%s ", timezone);
    putenv(timezone);

    return Py_BuildValue("s", "set timezone");
}

static PyObject *bme_forced_mode(PyObject *self, PyObject *args) {
    // Set BME68X config
    conf.os_hum = BME68X_OS_16X;
    conf.os_pres = BME68X_OS_1X;
    conf.os_temp = BME68X_OS_2X;
    conf.filter = BME68X_FILTER_OFF;
    conf.odr = BME68X_ODR_NONE;
    
    int8_t conf_rslt = bme68x_set_conf(&conf, &bme);
    if (conf_rslt == BME68X_OK) {
        // printf("\nBME68X CONF\n");
        // printf("os_hum = %#0x, os_pres = %#0x, os_temp = %#0x, filter = %#0x, odr = %#0x\n", conf.os_hum, conf.os_pres, conf.os_temp, conf.filter, conf.odr);
    } 
    else{
        perror("set BME68X config");
        exit(-1);
    } 

    // Set heater config
    heatr_conf.enable = BME68X_ENABLE;
    heatr_conf.heatr_temp = 300;
    heatr_conf.heatr_dur = 100;
    int8_t heatr_conf_rslt;
    heatr_conf_rslt = bme68x_set_heatr_conf(BME68X_FORCED_MODE, &heatr_conf, &bme);
    if (heatr_conf_rslt == BME68X_OK) {
        // printf("Set heater config\n");
    } 
    else {
        perror("bme68x_set_heatr_conf");
        exit(-1);
    } 

    return Py_BuildValue("s", "BME68X set to FORCED_MODE");
}

static PyObject *bme_get_data(PyObject *self, PyObject *args) {
    // Receive measurement data
    time_t t = time(NULL);
    struct tm tm = *localtime(&t);

    int8_t rslt;
    rslt = bme68x_set_op_mode(BME68X_FORCED_MODE, &bme);
    if (rslt != BME68X_OK) {
        perror("bme68x_set_op_mode");
        exit(-1);
    } 

    /* Calculate delay period in microseconds */
    del_period = bme68x_get_meas_dur(BME68X_FORCED_MODE, &conf, &bme) + (heatr_conf.heatr_dur * 1000);
    bme.delay_us(del_period, bme.intf_ptr);

    t = time(NULL);
	tm = *localtime(&t);

    /* Check if rslt == BME68X_OK, report or handle if otherwise */
    rslt = bme68x_get_data(BME68X_FORCED_MODE, &data, &n_fields, &bme);
    if (rslt != BME68X_OK) {
        perror("bme68x_get_data");
        exit(-1);
    }

    // printf("%d-%02d-%02d %02d:%02d:%02d ", tm.tm_year + 1900, tm.tm_mon + 1, tm.tm_mday, tm.tm_hour, tm.tm_min, tm.tm_sec);
    // printf("Tmp %.2f °C, Prs %.2f hPa, Hum %.2f %%rH, GsR %.2f k\u03a9, Status 0x%x\n",
        // data.temperature,
        // data.pressure/100,
        // data.humidity,
        // data.gas_resistance/1000,
        // data.status);

    return Py_BuildValue("[i,i,i,i,i,i,d,d,d,d,i]", tm.tm_year + 1900, tm.tm_mon + 1, tm.tm_mday, tm.tm_hour, tm.tm_min, tm.tm_sec, data.temperature, data.pressure, data.humidity, data.gas_resistance, data.status);
} 

static PyMethodDef bme_methods[] = {
    // "PythonName"         CName                       argument presentation       description
    {"init",                bme_init,                   METH_VARARGS,               "Initialize I2C and BME68X"},
    {"wiringPi_init",       bme_wiringPi_init,          METH_NOARGS,                "Initialize GPIO Pins, RED = 22, YLW = 27, GRN 17, BUZ = 16"},
    {"set_timezone",        bme_set_timezone,           METH_VARARGS,               "Change timezone (default = TZ=Europe/Berlin)"},
    {"forced_mode",         bme_forced_mode,            METH_NOARGS,                "Sets up BME68X sensor for FORCED MODE measurement"}, 
    {"get_data",            bme_get_data,               METH_VARARGS,               "Returns Array of BME68X outputs (as array of type double): year, month, day, hour, min, sec, temperature, pressure, humidity, gas resistance, status"},
    {NULL,                  NULL,                       0,                          NULL} // Sentinel
};

static struct PyModuleDef bme_module = {
    PyModuleDef_HEAD_INIT,
    "bme",
    bme_docstring,
    -1,
    bme_methods
};

PyMODINIT_FUNC PyInit_bme(void) {
    return PyModule_Create(&bme_module);
}

// MAIN
int main(){

    putenv(TIMEZONE);
    pi3g_wiringPi_init();

    uint8_t i2c_addr;
    uint8_t chip_id;
    int8_t rslt;
    rslt = pi3g_i2c_init(&linux_device_handle, &i2c_addr, &chip_id);

    // Initialize BME68X sensor
    bme.intf = BME68X_I2C_INTF;
    bme.amb_temp = AMB_TEMP;
    bme.read = pi3g_read;
    bme.write = pi3g_write;
    bme.delay_us = pi3g_delay_us;
    
    int8_t init_rslt = BME68X_OK;
    init_rslt = bme68x_init(&bme);
    if (init_rslt == BME68X_OK){
        printf("BME68X is initialized\n");
        if (bme.variant_id == BME68X_VARIANT_GAS_LOW) {
            printf("Variant = BME68X_VARIANT_GAS_LOW\n");
        } 
        else{
            printf("Variant = BME68X_VARIANT_GAS_HIGH\n");
        } 
    } 
    else{
        perror("initialize BME68X");
        exit(-1);
    } 

    // Set BME68X config
    conf.os_hum = BME68X_OS_16X;
    conf.os_pres = BME68X_OS_1X;
    conf.os_temp = BME68X_OS_2X;
    conf.filter = BME68X_FILTER_OFF;
    conf.odr = BME68X_ODR_NONE;
    
    int8_t conf_rslt = bme68x_set_conf(&conf, &bme);
    if (conf_rslt == BME68X_OK) {
        printf("\nBME68X CONF\n");
        printf("os_hum = %#0x, os_pres = %#0x, os_temp = %#0x, filter = %#0x, odr = %#0x\n", conf.os_hum, conf.os_pres, conf.os_temp, conf.filter, conf.odr);
    } 
    else{
        perror("set BME68X config");
        exit(-1);
    } 

    // Set heater config
    heatr_conf.enable = BME68X_ENABLE;
    heatr_conf.heatr_temp = 300;
    heatr_conf.heatr_dur = 100;
    int8_t heatr_conf_rslt;
    heatr_conf_rslt = bme68x_set_heatr_conf(BME68X_FORCED_MODE, &heatr_conf, &bme);
    if (heatr_conf_rslt == BME68X_OK) {
        printf("Set heater config\n");
    } 
    else {
        perror("bme68x_set_heatr_conf");
        exit(-1);
    } 

    // Receive measurement data
    time_t t = time(NULL);
    struct tm tm = *localtime(&t);
    printf("\nSTARTING MEASUREMENT\n");

    while (sample_count <= SAMPLE_COUNT) {
        rslt = bme68x_set_op_mode(BME68X_FORCED_MODE, &bme);
        if (rslt != BME68X_OK) {
            perror("bme68x_set_op_mode");
            exit(-1);
        } 

        /* Calculate delay period in microseconds */
        del_period = bme68x_get_meas_dur(BME68X_FORCED_MODE, &conf, &bme) + (heatr_conf.heatr_dur * 1000);
        bme.delay_us(del_period, bme.intf_ptr);

        t = time(NULL);
		tm = *localtime(&t);

        /* Check if rslt == BME68X_OK, report or handle if otherwise */
        rslt = bme68x_get_data(BME68X_FORCED_MODE, &data, &n_fields, &bme);
        if (rslt != BME68X_OK) {
            perror("bme68x_get_data");
            exit(-1);
        }

        if (n_fields) {
#ifdef BME68X_USE_FPU
            printf("%d-%02d-%02d %02d:%02d:%02d ", tm.tm_year + 1900, tm.tm_mon + 1, tm.tm_mday, tm.tm_hour, tm.tm_min, tm.tm_sec);
            printf("Nr %u, Tmp %.2f °C, Prs %.2f hPa, Hum %.2f %%rH, GsR %.2f k\u03a9, Status 0x%x\n",
                   sample_count,
                   // (long unsigned int)time_ms,
                   data.temperature,
                   data.pressure/100,
                   data.humidity,
                   data.gas_resistance/1000,
                   data.status);
#else
            printf("%u, %lu, %d, %lu, %lu, %lu, 0x%x\n",
                   sample_count,
                   (long unsigned int)time_ms,
                   (data.temperature / 100),
                   (long unsigned int)data.pressure,
                   (long unsigned int)(data.humidity / 1000),
                   (long unsigned int)data.gas_resistance,
                   data.status);
#endif
            sample_count++;
            sleep(3);
        }
    }

    if (!i2c_close(&linux_device_handle)) {
        printf("Closed I2C port\n");
    } 

    exit(0);
} 